"""Pytest plugin entry point."""

import pytest
from loguru import logger
from pytest_vigil.domains.reliability.models import TestExecution, ResourceLimit, InteractionType
from pytest_vigil.domains.reliability.services import PolicyService
from pytest_vigil.infrastructure.monitoring.loop import VigilMonitor
from pytest_vigil.infrastructure.enforcement.interrupt import Interrupter
from pytest_vigil.infrastructure.enforcement.signals import SignalManager, TimeoutException
from pytest_vigil.config import get_settings

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

def pytest_configure(config):
    """Configure the plugin."""
    config.addinivalue_line("markers", "vigil(**kwargs): Test reliability policies (timeout, memory, cpu)")
    # Ensure loguru doesn't interfere too much with pytest capture
    pass

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """
    Wrap the test execution to enforce limits.
    """
    settings = get_settings()
    limits = []
    
    # 1. Defaults from Settings (Environment / .env)
    timeout_val = settings.timeout
    memory_val = settings.memory_limit_mb
    cpu_val = settings.cpu_limit_percent

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

    # 3. Overrides from Markers
    # Marker overrides: @pytest.mark.vigil(timeout=5, memory=100)
    marker = item.get_closest_marker("vigil")
    if marker:
        if "timeout" in marker.kwargs:
            timeout_val = float(marker.kwargs["timeout"])
        if "memory" in marker.kwargs:
            memory_val = float(marker.kwargs["memory"])
        if "cpu" in marker.kwargs:
            cpu_val = float(marker.kwargs["cpu"])

    # Construct limits
    if timeout_val is not None:
        limits.append(ResourceLimit(limit_type=InteractionType.TIME, threshold=timeout_val, strict=settings.strict_mode))
    if memory_val is not None:
        limits.append(ResourceLimit(limit_type=InteractionType.MEMORY, threshold=memory_val, strict=settings.strict_mode))
    if cpu_val is not None:
        limits.append(ResourceLimit(limit_type=InteractionType.CPU, threshold=cpu_val, strict=settings.strict_mode))

    if not limits:
        yield
        return

    interrupter = Interrupter()
    signal_manager = SignalManager()
    signal_manager.install()
    
    execution = TestExecution(item_id=item.nodeid, node_id=item.nodeid)
    policy_service = PolicyService()
    
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
        yield
    except KeyboardInterrupt:
        raise
    finally:
        monitor.stop()
        signal_manager.restore()
