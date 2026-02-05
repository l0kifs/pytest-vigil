"""Pytest plugin entry point."""

import pytest
import os
import json
import psutil
from datetime import datetime, timezone
from loguru import logger
from _pytest.runner import runtestprotocol
from pytest_vigil.domains.reliability.models import TestExecution, ResourceLimit, InteractionType
from pytest_vigil.domains.reliability.services import PolicyService
from pytest_vigil.infrastructure.monitoring.loop import VigilMonitor
from pytest_vigil.infrastructure.enforcement.interrupt import Interrupter
from pytest_vigil.infrastructure.enforcement.signals import SignalManager, TimeoutException
from pytest_vigil.config import get_settings

# Store execution results for reporting
_execution_results = []
_flaky_tests = []

def pytest_sessionstart(session):
    """Initialize global result storage."""
    global _execution_results, _flaky_tests
    _execution_results = []
    _flaky_tests = []

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
        "--vigil-report",
        action="store",
        dest="vigil_report",
        help="Path to generate JSON report"
    )

def pytest_configure(config):
    """Configure the plugin."""
    config.addinivalue_line("markers", "vigil(**kwargs): Test reliability policies (timeout, memory, cpu, retry, stall_timeout)")
    # Ensure loguru doesn't interfere too much with pytest capture
    pass

def pytest_sessionfinish(session, exitstatus):
    """
    On xdist worker, sync results to controller.
    """
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
    
    try:
        for attempt in range(retry_count + 1):
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
                    "limits": [l.model_dump(mode='json') for l in limits]
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
                return True
            
            # If failed and attempts left
            if attempt < retry_count:
                logger.warning(f"Test {item.nodeid} failed attempt {attempt+1}/{retry_count+1}. Retrying...")
            else:
                item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
                
    finally:
        signal_manager.restore()

    return True

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Report detailed reliability metrics."""
    terminalreporter.section("Vigil Reliability Report")
    
    if _flaky_tests:
        terminalreporter.write_line("⚠️  Detected Flaky Tests (Passed on Retry):", yellow=True)
        for nodeid in _flaky_tests:
             terminalreporter.write_line(f"  - {nodeid}")
        terminalreporter.write_line("")

    if not _execution_results:
        terminalreporter.write_line("No reliability data collected.")
        return

    # simple table
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



