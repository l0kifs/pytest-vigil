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
                # Stall logic: if duration > threshold (wait time) AND cpu < secondary_threshold
                # We need access to history to properly detect stall over time, 
                # strictly speaking, "Stall" means "low CPU for at least X seconds".
                # Simplify: if current duration > X and *average* CPU of cached measurements (last 1s?) is low?
                # Or simplistic: if we are over stall timeout, check ONLY the current CPU. 
                # Better: Check if ALL measurements in the last `limit.threshold` seconds are below `secondary_threshold`.
                if duration > limit.threshold:
                     # Get measurements within the last `limit.threshold` seconds
                     # Actually, `threshold` is the time window we want to see inactivity.
                     # But `duration` keeps growing. We need to check if the *last X seconds* were idle.
                     # Since we don't have a sophisticated rolling window here easily without history traversal:
                     # Naive approach: if current CPU < limit.secondary_threshold and duration > limit.threshold.
                     # This might trigger false positives if the test simply waits for I/O.
                     # But "Deadlock Detection" usually implies strictness.
                     if limit.secondary_threshold is not None and cpu < limit.secondary_threshold:
                         return limit

        return None
