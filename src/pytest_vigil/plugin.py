"""Pytest plugin entry point."""

import pytest
import os
import json
from datetime import datetime, timezone
from loguru import logger
from _pytest.runner import runtestprotocol
from pytest_vigil.domains.reliability.models import TestExecution, ResourceLimit, InteractionType
from pytest_vigil.domains.reliability.services import PolicyService
from pytest_vigil.infrastructure.monitoring.loop import VigilMonitor
from pytest_vigil.infrastructure.monitoring.session import SessionMonitor
from pytest_vigil.infrastructure.enforcement.interrupt import Interrupter
from pytest_vigil.infrastructure.enforcement.signals import SignalManager
from pytest_vigil.config import get_settings

# Store execution results for reporting
_execution_results = []
_flaky_tests = []
_session_monitor = None
_current_test_nodeid = None

def pytest_sessionstart(session):
    """Initialize global result storage and session monitor."""
    global _execution_results, _flaky_tests, _session_monitor, _current_test_nodeid
    _execution_results = []
    _flaky_tests = []
    _current_test_nodeid = None
    
    # Setup session-level timeout if configured
    settings = get_settings()
    session_timeout = settings.session_timeout
    grace_period = settings.session_timeout_grace_period
    
    # CLI overrides
    cli_session_timeout = session.config.getoption("vigil_session_timeout")
    if cli_session_timeout is not None:
        session_timeout = float(cli_session_timeout)
    
    cli_grace_period = session.config.getoption("vigil_session_timeout_grace_period")
    if cli_grace_period is not None:
        grace_period = float(cli_grace_period)
    
    if session_timeout is not None and session_timeout > 0:
        # Apply CI multiplier if in CI environment
        is_ci = os.getenv("CI", "false").lower() == "true" or os.getenv("GITHUB_ACTIONS")
        multiplier = settings.ci_multiplier if is_ci else 1.0
        session_timeout *= multiplier
        
        _session_monitor = SessionMonitor(
            timeout=session_timeout,
            grace_period=grace_period,
            get_current_test=lambda: _current_test_nodeid
        )
        _session_monitor.start()
        logger.info(f"Session timeout set to {session_timeout}s (CI multiplier: {multiplier}x)")

def pytest_addoption(parser):
    """Register command line options."""
    group = parser.getgroup("vigil")
    group.addoption(
        "--vigil-timeout", 
        action="store", 
        dest="vigil_timeout",
        help="Timeout in seconds for each test"
    )
    group.addoption(
        "--vigil-memory", 
        action="store", 
        dest="vigil_memory",
        help="Memory limit in MB for each test"
    )
    group.addoption(
        "--vigil-cpu", 
        action="store", 
        dest="vigil_cpu",
        help="CPU limit in % for each test"
    )
    group.addoption(
        "--vigil-retry",
        action="store",
        dest="vigil_retry",
        help="Number of retries for failed/violation tests"
    )
    group.addoption(
        "--vigil-stall-timeout",
        action="store",
        dest="vigil_stall_timeout",
        help="Max duration in seconds of low CPU activity for stall detection"
    )
    group.addoption(
        "--vigil-stall-cpu-threshold",
        action="store",
        dest="vigil_stall_cpu_threshold",
        help="CPU threshold in % for stall detection"
    )
    group.addoption(
        "--vigil-report",
        action="store",
        dest="vigil_report",
        help="Path to generate JSON report"
    )
    group.addoption(
        "--vigil-session-timeout",
        action="store",
        dest="vigil_session_timeout",
        help="Global timeout in seconds for the entire test run session"
    )
    group.addoption(
        "--vigil-session-timeout-grace-period",
        action="store",
        dest="vigil_session_timeout_grace_period",
        help="Grace period in seconds after session timeout before forceful termination"
    )
    group.addoption(
        "--vigil-cli-report-verbosity",
        action="store",
        dest="vigil_cli_report_verbosity",
        choices=["none", "short", "full"],
        help="Control terminal report display: none (no report), short (summary stats), full (all tests)"
    )

def pytest_configure(config):
    """Configure the plugin."""
    config.addinivalue_line("markers", "vigil(**kwargs): Test reliability policies (timeout, memory, cpu, retry, stall_timeout)")
    # Ensure loguru doesn't interfere too much with pytest capture
    pass

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Track which test is currently running for session timeout reporting."""
    global _current_test_nodeid
    _current_test_nodeid = item.nodeid

@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item):
    """Clear current test tracking after test completes."""
    global _current_test_nodeid
    _current_test_nodeid = None

def pytest_sessionfinish(session, exitstatus):
    """
    On xdist worker, sync results to controller.
    Stop session monitor if active.
    """
    global _session_monitor
    
    # Stop session monitor
    if _session_monitor is not None:
        _session_monitor.stop()
        _session_monitor = None
    
    if hasattr(session.config, "workeroutput"):
        session.config.workeroutput["vigil_results"] = _execution_results
        session.config.workeroutput["vigil_flaky_tests"] = _flaky_tests

def pytest_testnodedown(node, error):
    """
    On xdist controller, receive results from worker.
    """
    if hasattr(node, "workeroutput"):
        if "vigil_results" in node.workeroutput:
            _execution_results.extend(node.workeroutput["vigil_results"])
        if "vigil_flaky_tests" in node.workeroutput:
            _flaky_tests.extend(node.workeroutput["vigil_flaky_tests"])

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    """
    Wrap the test execution to enforce limits and retry logic.
    Replaces standard runtestprotocol to enable per-attempt monitoring.
    """
    settings = get_settings()
    
    # CI Detection
    is_ci = os.getenv("CI", "false").lower() == "true" or os.getenv("GITHUB_ACTIONS")
    multiplier = settings.ci_multiplier if is_ci else 1.0

    # 1. Defaults from Settings
    timeout_val = settings.timeout
    memory_val = settings.memory_limit_mb
    cpu_val = settings.cpu_limit_percent
    retry_count = settings.retry_count
    stall_timeout = settings.stall_timeout
    stall_threshold = settings.stall_cpu_threshold

    # 2. Overrides from CLI
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

    # 3. Overrides from Markers
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

    # If no vigil, delegate to default runner
    if all(v is None for v in [timeout_val, memory_val, cpu_val, stall_timeout]) and retry_count == 0:
        return None

    # Apply Multiplier
    if timeout_val is not None:
        timeout_val *= multiplier
    if stall_timeout is not None:
        stall_timeout *= multiplier

    limits = []
    if timeout_val is not None:
        limits.append(ResourceLimit(limit_type=InteractionType.TIME, threshold=timeout_val, strict=settings.strict_mode))
    if memory_val is not None:
        limits.append(ResourceLimit(limit_type=InteractionType.MEMORY, threshold=memory_val, strict=settings.strict_mode))
    if cpu_val is not None:
        limits.append(ResourceLimit(limit_type=InteractionType.CPU, threshold=cpu_val, strict=settings.strict_mode))
    if stall_timeout is not None:
        limits.append(ResourceLimit(
            limit_type=InteractionType.STALL, 
            threshold=stall_timeout, 
            secondary_threshold=stall_threshold,
            strict=settings.strict_mode
        ))

    interrupter = Interrupter()
    signal_manager = SignalManager()
    signal_manager.install()
    policy_service = PolicyService()

    reports = []
    global _current_test_nodeid
    
    try:
        for attempt in range(retry_count + 1):
            # Track current test for session timeout reporting
            _current_test_nodeid = item.nodeid
            
            item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
            
            execution = TestExecution(item_id=item.nodeid, node_id=item.nodeid, retry_attempt=attempt)
            
            def on_violation(limit: ResourceLimit):
                interrupter.trigger(f"Policy violation: {limit}")

            monitor = VigilMonitor(
                execution=execution,
                limits=limits,
                policy_service=policy_service,
                on_violation=on_violation,
                interval=settings.monitor_interval
            )
            
            monitor.start()
            
            try:
                # Run the standard protocol for this item
                reports = runtestprotocol(item, nextitem=nextitem, log=False)
            except KeyboardInterrupt:
                monitor.stop()
                raise
            except Exception:
                monitor.stop()
                raise
            finally:
                monitor.stop()
            
            # Record stats
            if execution.measurements:
                max_cpu = max(m.cpu_percent for m in execution.measurements)
                max_mem = max(m.memory_mb for m in execution.measurements)
                _execution_results.append({
                    "node_id": item.nodeid,
                    "attempt": attempt,
                    "duration": execution.duration,
                    "max_cpu": max_cpu,
                    "max_memory": max_mem,
                    "limits": [limit.model_dump(mode='json') for limit in limits]
                })

            # Check if passed
            failed = any(r.failed for r in reports)
            
            # Report only if passed or if it's the final attempt
            if not failed or attempt == retry_count:
                for r in reports:
                    item.ihook.pytest_runtest_logreport(report=r)

            if not failed:
                if attempt > 0:
                    _flaky_tests.append(item.nodeid)
                item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
                _current_test_nodeid = None
                return True
            
            # If failed and attempts left
            if attempt < retry_count:
                logger.warning(f"Test {item.nodeid} failed attempt {attempt+1}/{retry_count+1}. Retrying...")
            else:
                item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
                
    finally:
        _current_test_nodeid = None
        signal_manager.restore()

    return True

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Report detailed reliability metrics."""
    settings = get_settings()
    
    # Get verbosity from CLI or settings
    verbosity = config.getoption("vigil_cli_report_verbosity")
    if verbosity is None:
        verbosity = settings.report_verbosity
    
    # If verbosity is 'none', skip reporting entirely
    if verbosity == "none":
        return
    
    terminalreporter.section("Vigil Reliability Report")
    
    if _flaky_tests:
        terminalreporter.write_line("⚠️  Detected Flaky Tests (Passed on Retry):", yellow=True)
        for nodeid in _flaky_tests:
             terminalreporter.write_line(f"  - {nodeid}")
        terminalreporter.write_line("")

    if not _execution_results:
        terminalreporter.write_line("No reliability data collected.")
        return

    # Short verbosity: show summary statistics only
    if verbosity == "short":
        total_count = len(_execution_results)
        durations = [r["duration"] for r in _execution_results]
        cpu_values = [r["max_cpu"] for r in _execution_results]
        memory_values = [r["max_memory"] for r in _execution_results]
        
        avg_duration = sum(durations) / total_count
        slowest = max(_execution_results, key=lambda r: r["duration"])
        fastest = min(_execution_results, key=lambda r: r["duration"])
        avg_cpu = sum(cpu_values) / total_count
        avg_memory = sum(memory_values) / total_count
        peak_cpu = max(cpu_values)
        peak_memory = max(memory_values)
        
        terminalreporter.write_line(f"Total Tests: {total_count}")
        terminalreporter.write_line(f"Average Duration: {avg_duration:.2f}s")
        terminalreporter.write_line(f"Fastest Test: {fastest['duration']:.2f}s ({fastest['node_id'].split('::')[-1]})")
        terminalreporter.write_line(f"Slowest Test: {slowest['duration']:.2f}s ({slowest['node_id'].split('::')[-1]})")
        terminalreporter.write_line(f"Average CPU: {avg_cpu:.1f}%")
        terminalreporter.write_line(f"Peak CPU: {peak_cpu:.1f}%")
        terminalreporter.write_line(f"Average Memory: {avg_memory:.1f} MB")
        terminalreporter.write_line(f"Peak Memory: {peak_memory:.1f} MB")
        terminalreporter.write_line(f"\n(Use --vigil-cli-report-verbosity=full to see all tests)")
    else:  # verbosity == "full"
        # Show detailed table
        headers = ["Test ID", "Att", "Duration (s)", "Max CPU (%)", "Max Mem (MB)"]
        
        # Find longest ID
        max_len = max((len(r["node_id"]) for r in _execution_results), default=20)
        # Ensure min length
        max_len = max(max_len, 20)
        
        fmt = f"{{:<{max_len}}} {{:>3}} {{:>12}} {{:>12}} {{:>12}}"
        
        terminalreporter.write_line(fmt.format(*headers))
        terminalreporter.write_line("-" * (max_len + 50))
        
        for res in _execution_results:
            terminalreporter.write_line(fmt.format(
                res["node_id"],
                res["attempt"],
                f"{res['duration']:.2f}",
                f"{res['max_cpu']:.1f}",
                f"{res['max_memory']:.1f}"
            ))

    # JSON Report
    report_path = config.getoption("vigil_report")
    if report_path:
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "flaky_tests": _flaky_tests,
            "results": _execution_results
        }
        with open(report_path, "w") as f:
            json.dump(data, f, indent=2)
        terminalreporter.write_line(f"\nSaved Vigil report to {report_path}")



