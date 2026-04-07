"""Pytest plugin entry point for pytest-vigil."""

import faulthandler
import os
from pathlib import Path
import pytest
from _pytest.runner import runtestprotocol, CallInfo
from _pytest.reports import TestReport
from pytest_vigil.infrastructure.observability.logging import get_logger

log = get_logger(__name__)

from pytest_vigil.config.settings import get_settings
from pytest_vigil.domains.reliability.models import (
    ExecutionResult,
    InteractionType,
    ResourceLimit,
    TestExecution,
)
from pytest_vigil.domains.reliability.services import PolicyService
from pytest_vigil.infrastructure.enforcement.interrupt import Interrupter
from pytest_vigil.infrastructure.enforcement.signals import SignalManager, TimeoutException
from pytest_vigil.infrastructure.monitoring.loop import VigilMonitor
from pytest_vigil.infrastructure.monitoring.session import SessionMonitor
from pytest_vigil.infrastructure.reporting.cli_reporter import CliReporter
from pytest_vigil.infrastructure.reporting.json_reporter import JsonReporter

# ---------------------------------------------------------------------------
# Session-scoped state (unavoidable for pytest plugin architecture)
# ---------------------------------------------------------------------------
_execution_results: list[ExecutionResult] = []
_flaky_tests: list[str] = []
_session_monitor: SessionMonitor | None = None
_current_test_nodeid: str | None = None
_last_test_nodeid: str | None = None


def pytest_sessionstart(session) -> None:
    """Initialize global result storage and start the session-level timeout monitor."""
    global _execution_results, _flaky_tests, _session_monitor, _current_test_nodeid, _last_test_nodeid
    _execution_results = []
    _flaky_tests = []
    _current_test_nodeid = None
    _last_test_nodeid = None

    settings = get_settings()
    session_timeout = settings.session_timeout
    grace_period = settings.session_timeout_grace_period

    cli_session_timeout = session.config.getoption("vigil_session_timeout")
    if cli_session_timeout is not None:
        session_timeout = float(cli_session_timeout)

    cli_grace_period = session.config.getoption("vigil_session_timeout_grace_period")
    if cli_grace_period is not None:
        grace_period = float(cli_grace_period)

    if session_timeout is not None and session_timeout > 0:
        multiplier = _ci_multiplier(settings)
        session_timeout *= multiplier

        _session_monitor = SessionMonitor(
            timeout=session_timeout,
            grace_period=grace_period,
            get_current_test=lambda: _current_test_nodeid,
            get_last_test=lambda: _last_test_nodeid,
        )
        _session_monitor.start()
        log.info("vigil: session timeout configured", timeout=session_timeout, ci_multiplier=multiplier)


def pytest_addoption(parser) -> None:
    """Register vigil command-line options."""
    group = parser.getgroup("vigil")
    group.addoption("--vigil-timeout",        action="store", dest="vigil_timeout",        help="Timeout in seconds for each test")
    group.addoption("--vigil-memory",         action="store", dest="vigil_memory",         help="Memory limit in MB for each test")
    group.addoption("--vigil-cpu",            action="store", dest="vigil_cpu",            help="CPU limit in %% for each test")
    group.addoption("--vigil-retry",          action="store", dest="vigil_retry",          help="Number of retries for failed/violation tests")
    group.addoption("--vigil-stall-timeout",  action="store", dest="vigil_stall_timeout",  help="Max duration in seconds of low CPU for stall detection")
    group.addoption("--vigil-stall-cpu-threshold", action="store", dest="vigil_stall_cpu_threshold", help="CPU threshold in %% for stall detection")
    group.addoption(
        "--vigil-json-report",
        action="store",
        nargs="?",
        const=True,
        default=None,
        dest="vigil_json_report",
        help="Enable JSON report generation (optionally accepts a custom path)",
    )
    group.addoption("--vigil-output-dir",     action="store", dest="vigil_output_dir",     help="Directory for generated Vigil artifacts")
    group.addoption("--vigil-session-timeout", action="store", dest="vigil_session_timeout", help="Global timeout in seconds for the entire test session")
    group.addoption("--vigil-session-timeout-grace-period", action="store", dest="vigil_session_timeout_grace_period", help="Grace period in seconds after session timeout before forceful termination")
    group.addoption("--vigil-cli-report-verbosity", action="store", dest="vigil_cli_report_verbosity", choices=["none", "short", "full"], help="Control terminal report display")
    group.addoption(
        "--vigil-force-exit-delay",
        action="store",
        dest="vigil_force_exit_delay",
        help=(
            "Seconds to wait after a soft interrupt before calling os._exit(124). "
            "Useful for tests stuck in GIL-holding C extensions that cannot be "
            "interrupted normally. Disabled by default."
        ),
    )


def pytest_configure(config) -> None:
    """Register the vigil marker."""
    config.addinivalue_line("markers", "vigil(**kwargs): Test reliability policies (timeout, memory, cpu, retry, stall_timeout)")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item) -> None:
    """Track which test is currently running."""
    global _current_test_nodeid, _last_test_nodeid
    _current_test_nodeid = item.nodeid
    _last_test_nodeid = item.nodeid


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item) -> None:
    """Clear the currently-running test tracker."""
    global _current_test_nodeid
    _current_test_nodeid = None


def pytest_sessionfinish(session, exitstatus) -> None:
    """Stop the session monitor and propagate results to the xdist controller."""
    global _session_monitor
    if _session_monitor is not None:
        _session_monitor.stop()
        _session_monitor = None

    if hasattr(session.config, "workeroutput"):
        session.config.workeroutput["vigil_results"] = [r.model_dump(mode="json") for r in _execution_results]
        session.config.workeroutput["vigil_flaky_tests"] = _flaky_tests


def pytest_testnodedown(node, error) -> None:
    """Collect results from xdist worker nodes."""
    if hasattr(node, "workeroutput"):
        if "vigil_results" in node.workeroutput:
            _execution_results.extend(
                ExecutionResult.model_validate(r) for r in node.workeroutput["vigil_results"]
            )
        if "vigil_flaky_tests" in node.workeroutput:
            _flaky_tests.extend(node.workeroutput["vigil_flaky_tests"])


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem) -> bool | None:
    """Run the test with Vigil monitoring, retry logic, and resource enforcement."""
    settings = get_settings()
    multiplier = _ci_multiplier(settings)

    timeout_val = settings.timeout
    memory_val = settings.memory_limit_mb
    cpu_val = settings.cpu_limit_percent
    retry_count = settings.retry_count
    stall_timeout = settings.stall_timeout
    stall_threshold = settings.stall_cpu_threshold
    force_exit_delay = settings.force_exit_delay

    # CLI overrides
    cli_timeout = item.config.getoption("vigil_timeout")
    if cli_timeout is not None:
        timeout_val = float(cli_timeout)
    cli_memory = item.config.getoption("vigil_memory")
    if cli_memory is not None:
        memory_val = float(cli_memory)
    cli_cpu = item.config.getoption("vigil_cpu")
    if cli_cpu is not None:
        cpu_val = float(cli_cpu)
    cli_retry = item.config.getoption("vigil_retry")
    if cli_retry is not None:
        retry_count = int(cli_retry)
    cli_stall_timeout = item.config.getoption("vigil_stall_timeout")
    if cli_stall_timeout is not None:
        stall_timeout = float(cli_stall_timeout)
    cli_stall_threshold = item.config.getoption("vigil_stall_cpu_threshold")
    if cli_stall_threshold is not None:
        stall_threshold = float(cli_stall_threshold)
    cli_force_exit_delay = item.config.getoption("vigil_force_exit_delay")
    if cli_force_exit_delay is not None:
        force_exit_delay = float(cli_force_exit_delay)

    # Marker overrides
    marker = item.get_closest_marker("vigil")
    if marker:
        if "timeout" in marker.kwargs:
            timeout_val = float(marker.kwargs["timeout"])
        if "memory" in marker.kwargs:
            memory_val = float(marker.kwargs["memory"])
        if "cpu" in marker.kwargs:
            cpu_val = float(marker.kwargs["cpu"])
        if "retry" in marker.kwargs:
            retry_count = int(marker.kwargs["retry"])
        if "stall_timeout" in marker.kwargs:
            stall_timeout = float(marker.kwargs["stall_timeout"])
        if "stall_cpu_threshold" in marker.kwargs:
            stall_threshold = float(marker.kwargs["stall_cpu_threshold"])

    if all(v is None for v in [timeout_val, memory_val, cpu_val, stall_timeout]) and retry_count == 0:
        return None

    if timeout_val is not None:
        timeout_val *= multiplier
    if stall_timeout is not None:
        stall_timeout *= multiplier

    limits: list[ResourceLimit] = []
    if timeout_val is not None:
        limits.append(ResourceLimit(limit_type=InteractionType.TIME, threshold=timeout_val, strict=settings.strict_mode))
    if memory_val is not None:
        limits.append(ResourceLimit(limit_type=InteractionType.MEMORY, threshold=memory_val, strict=settings.strict_mode))
    if cpu_val is not None:
        limits.append(ResourceLimit(limit_type=InteractionType.CPU, threshold=cpu_val, strict=settings.strict_mode))
    if stall_timeout is not None:
        limits.append(ResourceLimit(limit_type=InteractionType.STALL, threshold=stall_timeout, secondary_threshold=stall_threshold, strict=settings.strict_mode))

    interrupter = Interrupter(force_exit_delay=force_exit_delay)
    signal_manager = SignalManager()
    signal_manager.install()
    policy_service = PolicyService()

    global _current_test_nodeid

    try:
        for attempt in range(retry_count + 1):
            _current_test_nodeid = item.nodeid
            item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
            execution = TestExecution(item_id=item.nodeid, node_id=item.nodeid, retry_attempt=attempt)

            def on_violation(limit: ResourceLimit) -> None:
                interrupter.trigger(f"Policy violation: {limit}")

            # Set the kernel-level alarm backstop for this attempt.
            # This fires even if the monitoring thread dies or is delayed.
            if timeout_val is not None:
                signal_manager.set_alarm(timeout_val)

            # Enable faulthandler diagnostics: writes C-level thread tracebacks to
            # fd 2 (real stderr) if the test is still running after timeout_val + 1 s.
            # We open fd 2 directly (bypassing Python-level capture) so the output
            # reaches the real pipe/terminal even when pytest's capture is active.
            _faulthandler_active = False
            _faulthandler_file = None
            if timeout_val is not None and hasattr(faulthandler, "dump_traceback_later"):
                try:
                    import io
                    _faulthandler_file = io.FileIO(2, closefd=False)
                    faulthandler.dump_traceback_later(timeout_val + 1.0, repeat=False, file=_faulthandler_file)
                    _faulthandler_active = True
                except Exception:
                    pass

            monitor = VigilMonitor(
                execution=execution,
                limits=limits,
                policy_service=policy_service,
                on_violation=on_violation,
                interval=settings.monitor_interval,
            )
            monitor.start()

            timed_out = False
            try:
                reports = runtestprotocol(item, nextitem=nextitem, log=False)
            except KeyboardInterrupt:
                # Cancel alarm BEFORE monitor.stop() so SIGALRM cannot fire
                # inside thread.join() and kill the xdist worker.
                signal_manager.cancel_alarm()
                if _faulthandler_active and hasattr(faulthandler, "cancel_dump_traceback_later"):
                    faulthandler.cancel_dump_traceback_later()
                interrupter.cancel_escalation()
                monitor.stop()
                raise
            except BaseException as exc:
                # TimeoutException is a BaseException subclass (not Exception), so it
                # falls through a plain `except Exception` block and would otherwise
                # propagate uncaught through the retry loop, through
                # pytest_runtest_protocol, and ultimately kill the xdist worker with
                # "Unexpectedly no active workers available".
                #
                # Instead: cancel the alarm FIRST (before monitor.stop() / thread.join())
                # to prevent a second SIGALRM delivery from firing inside threading
                # internals (lock.acquire), then synthesize a proper FAILED report so
                # pytest records the timeout as a normal test failure and moves on.
                signal_manager.cancel_alarm()
                if _faulthandler_active and hasattr(faulthandler, "cancel_dump_traceback_later"):
                    faulthandler.cancel_dump_traceback_later()
                interrupter.cancel_escalation()
                monitor.stop()
                if isinstance(exc, TimeoutException):
                    timed_out = True
                    _captured_exc = exc

                    def _raise_timeout():
                        raise _captured_exc

                    timeout_call = CallInfo.from_call(_raise_timeout, when="call")
                    reports = [TestReport.from_item_and_call(item, timeout_call)]
                    log.warning("vigil: test timed out", nodeid=item.nodeid)
                else:
                    raise
            finally:
                # Safety net: cancel alarm and stop monitor even if the branches above
                # already did so (cancel_alarm and stop() are idempotent).
                signal_manager.cancel_alarm()
                if _faulthandler_active and hasattr(faulthandler, "cancel_dump_traceback_later"):
                    faulthandler.cancel_dump_traceback_later()
                interrupter.cancel_escalation()
                monitor.stop()

            if execution.measurements:
                max_cpu = max(m.cpu_percent for m in execution.measurements)
                max_mem = max(m.memory_mb   for m in execution.measurements)
                cpu_breakdown_aggregate: dict[str, float] = {}
                for m in execution.measurements:
                    for process_type, cpu_value in m.cpu_breakdown.items():
                        cpu_breakdown_aggregate[process_type] = max(
                            cpu_breakdown_aggregate.get(process_type, cpu_value), cpu_value
                        )
                _execution_results.append(ExecutionResult(
                    node_id=item.nodeid,
                    attempt=attempt,
                    duration=execution.duration,
                    max_cpu=max_cpu,
                    max_memory=max_mem,
                    cpu_breakdown=cpu_breakdown_aggregate,
                    limits=limits,
                ))

            failed = any(r.failed for r in reports)
            if not failed or attempt == retry_count:
                for r in reports:
                    item.ihook.pytest_runtest_logreport(report=r)

            if not failed:
                if attempt > 0:
                    _flaky_tests.append(item.nodeid)
                item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
                _current_test_nodeid = None
                return True

            if attempt < retry_count:
                log.warning("vigil: test failed, retrying", nodeid=item.nodeid, attempt=attempt + 1, max_attempts=retry_count + 1)
            else:
                item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
    finally:
        _current_test_nodeid = None
        signal_manager.restore()

    return True


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Render the Vigil reliability section and optionally write the JSON report."""
    settings = get_settings()
    verbosity = config.getoption("vigil_cli_report_verbosity")
    if verbosity is None:
        verbosity = settings.console_report_verbosity

    CliReporter().report(
        terminalreporter=terminalreporter,
        results=_execution_results,
        flaky_tests=_flaky_tests,
        verbosity=verbosity,
    )

    report_option = config.getoption("vigil_json_report")
    if report_option is None:
        report_option = settings.json_report
    if report_option:
        output_dir = config.getoption("vigil_output_dir")
        if output_dir is None:
            output_dir = settings.artifacts_dir
        report_target = report_option if isinstance(report_option, str) else settings.json_report_filename
        resolved_report_path = _resolve_artifact_path(report_target, output_dir)
        JsonReporter().save(
            path=resolved_report_path,
            results=_execution_results,
            flaky_tests=_flaky_tests,
        )
        terminalreporter.write_line(f"\nSaved Vigil report to {resolved_report_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ci_multiplier(settings) -> float:
    """Return the CI timeout multiplier when running in a CI environment."""
    is_ci = os.getenv("CI", "false").lower() == "true" or bool(os.getenv("GITHUB_ACTIONS"))
    return settings.ci_multiplier if is_ci else 1.0


def _resolve_artifact_path(path: str, output_dir: str) -> str:
    """Resolve generated artifact path to an absolute or output-dir-relative target."""
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str(Path(output_dir) / candidate)
