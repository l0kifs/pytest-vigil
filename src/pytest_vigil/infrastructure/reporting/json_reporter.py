"""JSON report writer for Vigil reliability results."""

import json
from datetime import datetime, timezone
from typing import List
from loguru import logger
from pytest_vigil.domains.reliability.models import ExecutionResult


class JsonReporter:
    """Serializes Vigil reliability results to a JSON file."""

    def save(self, path: str, results: List[ExecutionResult], flaky_tests: List[str]) -> None:
        """Write results to a JSON file.

        Args:
            path: File path to write the report to.
            results: Collected execution results for this session.
            flaky_tests: Node IDs of tests that passed only after a retry.
        """
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "flaky_tests": flaky_tests,
            "results": [
                {
                    "node_id": r.node_id,
                    "attempt": r.attempt,
                    "duration": r.duration,
                    "max_cpu": r.max_cpu,
                    "max_memory": r.max_memory,
                    "cpu_breakdown": r.cpu_breakdown,
                    "limits": [limit.model_dump(mode="json") for limit in r.limits],
                }
                for r in results
            ],
        }
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Vigil JSON report saved to {path}")
        except OSError as exc:
            logger.error(f"Failed to write Vigil JSON report to {path}: {exc}")
