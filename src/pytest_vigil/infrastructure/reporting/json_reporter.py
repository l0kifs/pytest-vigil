"""JSON report writer for Vigil reliability results."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from pytest_vigil.infrastructure.observability.logging import get_logger

log = get_logger(__name__)
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
            report_path = Path(path)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with report_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            log.info("vigil.json_reporter: report saved", path=path)
        except OSError:
            log.exception("vigil.json_reporter: failed to write report", path=path)
