"""
Tests for the VigilMonitor stop-event responsiveness fix (Item 2).

Replacing time.sleep() with _stop_event.wait() means stop() wakes the
monitoring thread immediately instead of waiting up to interval seconds.

Tests here verify:
- Violations are still detected after the change (regression).
- Monitor stops quickly when stop() is called.
- No stray violation fires after stop() returns.
- The fix does not affect normal test flows.
"""

import threading
import time

import pytest

pytest_plugins = ["pytester"]


class TestVigilMonitorStopResponsiveness:
    """stop() returns without waiting a full interval after the change."""

    def test_violations_still_detected_after_fix(self, pytester):
        """Timeout violation is still enforced after the time.sleep → wait change."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.4)
            def test_slow():
                time.sleep(2)
        """)
        result = pytester.runpytest()
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1

    def test_passing_test_undisturbed(self, pytester):
        """Tests that finish before the limit are unaffected."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_quick():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_stop_is_fast(self):
        """stop() returns in well under one interval when called from outside."""
        from pytest_vigil.domains.reliability.models import TestExecution, ResourceLimit, InteractionType
        from pytest_vigil.domains.reliability.services import PolicyService
        from pytest_vigil.infrastructure.monitoring.loop import VigilMonitor

        execution = TestExecution(item_id="test_stop_fast", node_id="test_stop_fast")
        limits = [ResourceLimit(limit_type=InteractionType.TIME, threshold=60.0, strict=True)]
        policy_service = PolicyService()

        violations = []

        monitor = VigilMonitor(
            execution=execution,
            limits=limits,
            policy_service=policy_service,
            on_violation=lambda l: violations.append(l),
            interval=0.5,  # largo interval to make the improvement obvious
        )
        monitor.start()
        time.sleep(0.05)  # let the thread enter its wait

        t0 = time.monotonic()
        monitor.stop()
        elapsed = time.monotonic() - t0

        # With _stop_event.wait() the thread wakes up immediately; without it
        # we would wait up to interval (0.5 s).  Allow generous headroom.
        assert elapsed < 0.4, f"stop() took {elapsed:.3f}s — expected < 0.4s"
        assert violations == [], "No violation should have fired"

    def test_no_violation_after_stop(self):
        """Once stop() returns the on_violation callback is never called again."""
        from pytest_vigil.domains.reliability.models import TestExecution, ResourceLimit, InteractionType
        from pytest_vigil.domains.reliability.services import PolicyService
        from pytest_vigil.infrastructure.monitoring.loop import VigilMonitor

        execution = TestExecution(item_id="test_no_violation_after_stop", node_id="test_no_violation_after_stop")
        # Low threshold so a violation would fire immediately if monitoring continues.
        limits = [ResourceLimit(limit_type=InteractionType.TIME, threshold=0.0, strict=True)]
        policy_service = PolicyService()

        violations = []
        monitor = VigilMonitor(
            execution=execution,
            limits=limits,
            policy_service=policy_service,
            on_violation=lambda l: violations.append(l),
            interval=0.05,
        )
        monitor.start()
        # Let at least one violation fire.
        time.sleep(0.15)
        monitor.stop()
        count_after_stop = len(violations)

        # Wait another cycle and confirm no new violations.
        time.sleep(0.15)
        assert len(violations) == count_after_stop, "Violation fired after stop()"

    def test_monitor_thread_exits_after_stop(self):
        """The monitoring thread is no longer alive shortly after stop() returns."""
        from pytest_vigil.domains.reliability.models import TestExecution, ResourceLimit, InteractionType
        from pytest_vigil.domains.reliability.services import PolicyService
        from pytest_vigil.infrastructure.monitoring.loop import VigilMonitor

        execution = TestExecution(item_id="test_thread_exits", node_id="test_thread_exits")
        limits = [ResourceLimit(limit_type=InteractionType.TIME, threshold=60.0, strict=True)]
        policy_service = PolicyService()

        monitor = VigilMonitor(
            execution=execution,
            limits=limits,
            policy_service=policy_service,
            on_violation=lambda l: None,
            interval=0.5,
        )
        monitor.start()
        assert monitor._thread is not None and monitor._thread.is_alive()

        monitor.stop()
        # The thread is a daemon; after stop() it should not be alive.
        assert monitor._thread is None or not monitor._thread.is_alive()

    def test_multiple_starts_and_stops(self, pytester):
        """Multiple vigil-decorated tests run sequentially without monitor leaks."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_a():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_b():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_c():
                time.sleep(0.05)
        """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=3)


class TestVigilMonitorStopEventCorrectness:
    """Edge-cases around the stop-event semantics."""

    def test_stop_before_start_is_safe(self):
        """Calling stop() before start() should not raise."""
        from pytest_vigil.domains.reliability.models import TestExecution, ResourceLimit, InteractionType
        from pytest_vigil.domains.reliability.services import PolicyService
        from pytest_vigil.infrastructure.monitoring.loop import VigilMonitor

        execution = TestExecution(item_id="pre_start_stop", node_id="pre_start_stop")
        limits = [ResourceLimit(limit_type=InteractionType.TIME, threshold=60.0, strict=True)]
        monitor = VigilMonitor(
            execution=execution,
            limits=limits,
            policy_service=PolicyService(),
            on_violation=lambda l: None,
        )
        monitor.stop()  # should not raise

    def test_double_stop_is_safe(self):
        """Calling stop() twice should not raise."""
        from pytest_vigil.domains.reliability.models import TestExecution, ResourceLimit, InteractionType
        from pytest_vigil.domains.reliability.services import PolicyService
        from pytest_vigil.infrastructure.monitoring.loop import VigilMonitor

        execution = TestExecution(item_id="double_stop", node_id="double_stop")
        limits = [ResourceLimit(limit_type=InteractionType.TIME, threshold=60.0, strict=True)]
        monitor = VigilMonitor(
            execution=execution,
            limits=limits,
            policy_service=PolicyService(),
            on_violation=lambda l: None,
            interval=0.1,
        )
        monitor.start()
        monitor.stop()
        monitor.stop()  # second call must not raise
