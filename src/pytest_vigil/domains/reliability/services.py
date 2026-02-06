"""Domain services for reliability logic."""

from typing import List, Optional
from loguru import logger
from pytest_vigil.domains.reliability.models import TestExecution, ResourceLimit, InteractionType

class PolicyService:
    """Service to evaluate test execution against reliability policies."""

    def check_violation(self, execution: TestExecution, limits: List[ResourceLimit]) -> Optional[ResourceLimit]:
        """Checks if the current execution violates any resource limits."""
        duration = execution.duration
        
        # Get latest measurement if available
        cpu = 0.0
        memory = 0.0
        if execution.measurements:
            latest = execution.measurements[-1]
            cpu = latest.cpu_percent
            memory = latest.memory_mb

        for limit in limits:
            if limit.limit_type == InteractionType.TIME:
                if duration > limit.threshold:
                    return limit
            elif limit.limit_type == InteractionType.MEMORY:
                if memory > limit.threshold:
                    return limit
            elif limit.limit_type == InteractionType.CPU:
                if cpu > limit.threshold:
                    return limit
            elif limit.limit_type == InteractionType.STALL:
                # Stall detection: Check if CPU has been consistently low for at least `limit.threshold` seconds
                # threshold = stall_timeout (time window, e.g., 0.5s)
                # secondary_threshold = stall_cpu_threshold (CPU percentage, e.g., 1.0%)
                if limit.secondary_threshold is not None and execution.measurements and duration >= limit.threshold:
                    # Only check after test has been running for at least stall_timeout
                    # Get current time
                    from datetime import datetime, timedelta
                    now = datetime.now()
                    stall_window_start = now - timedelta(seconds=limit.threshold)
                    
                    # Find measurements within the stall time window (last `stall_timeout` seconds)
                    window_measurements = [
                        m for m in execution.measurements 
                        if m.timestamp >= stall_window_start
                    ]
                    
                    # Check if all measurements in window show low CPU
                    if window_measurements:
                        all_below_threshold = all(
                            m.cpu_percent <= limit.secondary_threshold 
                            for m in window_measurements
                        )
                        if all_below_threshold:
                            return limit

        return None
