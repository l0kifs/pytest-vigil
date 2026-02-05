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
        return None
