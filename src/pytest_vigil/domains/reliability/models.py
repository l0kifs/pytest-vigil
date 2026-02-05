"""Domain models for test reliability and monitoring."""

from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

class InteractionType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    TIME = "time"

class ResourceLimit(BaseModel):
    """Defines a limit for a specific resource."""
    limit_type: InteractionType
    threshold: float
    strict: bool = True
    
    model_config = ConfigDict(frozen=True)

class TestOutcome(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    RESOURCE_ERROR = "resource_error"

class ExecutionMeasurement(BaseModel):
    """Single point in time measurement of resources."""
    timestamp: datetime = Field(default_factory=datetime.now)
    cpu_percent: float
    memory_mb: float

class TestExecution(BaseModel):
    """Represents a single test execution context."""
    item_id: str
    node_id: str
    start_time: datetime = Field(default_factory=datetime.now)
    measurements: List[ExecutionMeasurement] = Field(default_factory=list)
    outcome: Optional[TestOutcome] = None

    def add_measurement(self, cpu: float, memory: float) -> None:
        self.measurements.append(ExecutionMeasurement(
            cpu_percent=cpu,
            memory_mb=memory
        ))

    @property
    def duration(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()
