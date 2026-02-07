"""Monitoring loop infrastructure."""

import threading
import time
from typing import List, Callable, Optional
from loguru import logger
from pytest_vigil.domains.reliability.models import TestExecution, ResourceLimit
from pytest_vigil.domains.reliability.services import PolicyService
from pytest_vigil.infrastructure.monitoring.system import SystemMonitor

class VigilMonitor:
    """Manages the background monitoring thread for a test execution."""

    def __init__(
        self, 
        execution: TestExecution, 
        limits: List[ResourceLimit],
        policy_service: PolicyService,
        on_violation: Callable[[ResourceLimit], None],
        interval: float = 0.1
    ):
        self.execution = execution
        self.limits = limits
        self.policy_service = policy_service
        self.on_violation = on_violation
        self.interval = interval
        self._stop_event = threading.Event()
        self._monitor = SystemMonitor()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Starts the monitoring thread."""
        self._thread = threading.Thread(
            target=self._run, 
            daemon=True, 
            name=f"vigil-monitor-{self.execution.item_id}"
        )
        self._thread.start()

    def stop(self) -> None:
        """Stops the monitoring thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        # Initialize CPU counter (first call often irrelevant)
        self._monitor.get_stats()
        
        iteration = 0
        while not self._stop_event.is_set():
            try:
                # Collect detailed stats every 10 iterations to reduce overhead
# For other iterations, use simple stats
                if iteration % 10 == 0:
                    cpu, mem, cpu_breakdown = self._monitor.get_detailed_stats()
                    self.execution.add_measurement(cpu, mem, cpu_breakdown)
                else:
                    cpu, mem = self._monitor.get_stats()
                    self.execution.add_measurement(cpu, mem, {})
                
                iteration += 1
                
                violation = self.policy_service.check_violation(self.execution, self.limits)
                if violation:
                    # Callback
                    self.on_violation(violation)
                    if violation.strict:
                        break
            except Exception as e:
                # Reliability: Plugin crash shouldn't affect suite
                logger.error(f"Vigil monitor error: {e}")
                break
            
            time.sleep(self.interval)
