"""CLI terminal reporter for Vigil reliability results."""

from typing import List
from pytest_vigil.domains.reliability.models import ExecutionResult


class CliReporter:
    """Writes the Vigil reliability report to the pytest terminal."""

    def report(
        self,
        terminalreporter,
        results: List[ExecutionResult],
        flaky_tests: List[str],
        verbosity: str,
    ) -> None:
        """Render the reliability section in the terminal summary.

        Args:
            terminalreporter: pytest's TerminalReporter instance.
            results: Collected execution results for this session.
            flaky_tests: Node IDs of tests that passed only after a retry.
            verbosity: One of "none", "short", or "full".
        """
        if verbosity == "none":
            return

        terminalreporter.section("Vigil Reliability Report")

        if flaky_tests:
            terminalreporter.write_line("⚠️  Detected Flaky Tests (Passed on Retry):", yellow=True)
            for nodeid in flaky_tests:
                terminalreporter.write_line(f"  - {nodeid}")
            terminalreporter.write_line("")

        if not results:
            terminalreporter.write_line("No reliability data collected.")
            return

        if verbosity == "short":
            self._write_short(terminalreporter, results)
        else:
            self._write_full(terminalreporter, results)

    def _write_short(self, terminalreporter, results: List[ExecutionResult]) -> None:
        total_count = len(results)
        durations = [r.duration for r in results]
        cpu_values = [r.max_cpu for r in results]
        memory_values = [r.max_memory for r in results]
        avg_duration = sum(durations) / total_count
        slowest = max(results, key=lambda r: r.duration)
        fastest = min(results, key=lambda r: r.duration)

        terminalreporter.write_line(f"Total Tests: {total_count}")
        terminalreporter.write_line(f"Average Duration: {avg_duration:.2f}s")
        terminalreporter.write_line(f"Fastest Test: {fastest.duration:.2f}s ({fastest.node_id.split('::')[-1]})")
        terminalreporter.write_line(f"Slowest Test: {slowest.duration:.2f}s ({slowest.node_id.split('::')[-1]})")
        terminalreporter.write_line(f"Average CPU: {sum(cpu_values) / total_count:.1f}%")
        terminalreporter.write_line(f"Peak CPU: {max(cpu_values):.1f}%")
        terminalreporter.write_line(f"Average Memory: {sum(memory_values) / total_count:.1f} MB")
        terminalreporter.write_line(f"Peak Memory: {max(memory_values):.1f} MB")

        total_breakdown: dict = {}
        for r in results:
            for process_type, cpu_value in r.cpu_breakdown.items():
                total_breakdown[process_type] = max(total_breakdown.get(process_type, cpu_value), cpu_value)

        if total_breakdown:
            terminalreporter.write_line("\nPeak CPU by Process Type:")
            for process_type, cpu_value in sorted(total_breakdown.items(), key=lambda x: x[1], reverse=True):
                terminalreporter.write_line(f"  {process_type.capitalize()}: {cpu_value:.1f}%")

        terminalreporter.write_line("\n(Use --vigil-cli-report-verbosity=full to see all tests)")

    def _write_full(self, terminalreporter, results: List[ExecutionResult]) -> None:
        headers = ["Test ID", "Att", "Duration (s)", "Max CPU (%)", "Max Mem (MB)"]
        max_len = max(max((len(r.node_id) for r in results), default=20), 20)
        fmt = f"{{:<{max_len}}} {{:>3}} {{:>12}} {{:>12}} {{:>12}}"
        terminalreporter.write_line(fmt.format(*headers))
        terminalreporter.write_line("-" * (max_len + 50))
        for res in results:
            terminalreporter.write_line(fmt.format(
                res.node_id, res.attempt,
                f"{res.duration:.2f}", f"{res.max_cpu:.1f}", f"{res.max_memory:.1f}",
            ))
