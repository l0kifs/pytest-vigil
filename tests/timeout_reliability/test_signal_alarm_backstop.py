"""
Tests for the signal.alarm() kernel-level backstop (Item 1).

The backstop fires a SIGALRM via the OS kernel, independently of whether the
monitoring thread is alive.  Tests here verify:

- Timeouts still work end-to-end with the alarm active (regression).
- The alarm is cancelled properly so it does not fire into a subsequent test.
- Per-attempt alarm reset works correctly under the retry mechanism.
- The SignalManager API (set_alarm / cancel_alarm / restore) behaves correctly
  in isolation.
"""

import signal
import sys
import pytest

pytest_plugins = ["pytester"]


class TestSignalAlarmBackstopRegression:
    """Existing timeout behaviour is preserved with the alarm backstop active."""

    def test_timeout_still_enforced_with_alarm(self, pytester):
        """Timeout fires even with the OS alarm backstop in place."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_slow():
                time.sleep(2)
        """)
        result = pytester.runpytest()
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1

    def test_passing_test_not_affected_by_alarm(self, pytester):
        """A test that finishes before the timeout completes successfully."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_quick():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_alarm_does_not_fire_into_next_test(self, pytester):
        """After a timed-out test the alarm is cancelled; the next unguarded test passes."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_times_out():
                time.sleep(2)

            def test_afterwards():
                # No vigil marker — must not be interrupted by a stray alarm.
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-v")
        # First test fails, second must pass.
        result.assert_outcomes(passed=1, failed=1)

    def test_alarm_does_not_fire_into_subsequent_vigil_test(self, pytester):
        """A stray alarm from attempt N does not fire during attempt N+1."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_first_times_out():
                time.sleep(2)

            @pytest.mark.vigil(timeout=2.0)
            def test_second_passes():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1, failed=1)

    def test_alarm_reset_between_retries(self, pytester):
        """Each retry attempt gets a fresh alarm so retries work correctly."""
        pytester.makepyfile("""
            import pytest
            import time

            _attempt = [0]

            @pytest.mark.vigil(timeout=1.0, retry=2)
            def test_flaky():
                _attempt[0] += 1
                if _attempt[0] < 3:
                    raise AssertionError("not yet")
                # Third attempt succeeds quickly — must not be killed by stale alarm.
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-v")
        assert result.ret == 0

    def test_alarm_not_set_without_timeout(self, pytester):
        """No alarm is set when only memory / CPU limits are configured."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=999)
            def test_memory_only():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_multiple_tests_sequential_alarms(self, pytester):
        """Several consecutive timeout-bound tests each receive their own alarm."""
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


@pytest.mark.skipif(not hasattr(signal, "SIGALRM"), reason="SIGALRM not available on this platform")
class TestSignalManagerUnit:
    """Unit-level tests for SignalManager.set_alarm() and cancel_alarm()."""

    def test_set_alarm_rounds_up_to_one_second_minimum(self):
        from pytest_vigil.infrastructure.enforcement.signals import SignalManager
        mgr = SignalManager()
        mgr.install()
        try:
            mgr.set_alarm(0.1)   # 0.1 s → ceil → 1 s minimum
            remaining = signal.alarm(0)  # cancel and read
            assert remaining >= 1
        finally:
            mgr.restore()

    def test_set_alarm_rounds_up_fractional_seconds(self):
        from pytest_vigil.infrastructure.enforcement.signals import SignalManager
        mgr = SignalManager()
        mgr.install()
        try:
            mgr.set_alarm(1.3)   # ceil(1.3) = 2
            remaining = signal.alarm(0)
            assert remaining >= 2
        finally:
            mgr.restore()

    def test_cancel_alarm_cancels_pending_alarm(self):
        from pytest_vigil.infrastructure.enforcement.signals import SignalManager
        mgr = SignalManager()
        mgr.install()
        try:
            mgr.set_alarm(10.0)
            mgr.cancel_alarm()
            remaining = signal.alarm(0)
            assert remaining == 0
        finally:
            mgr.restore()

    def test_restore_cancels_pending_alarm(self):
        from pytest_vigil.infrastructure.enforcement.signals import SignalManager
        mgr = SignalManager()
        mgr.install()
        mgr.set_alarm(10.0)
        mgr.restore()  # must cancel the alarm
        # After restore the old handler is in place; set a 0 alarm to check no pending alarm.
        remaining = signal.alarm(0)
        assert remaining == 0

    def test_cancel_alarm_without_pending_is_safe(self):
        from pytest_vigil.infrastructure.enforcement.signals import SignalManager
        mgr = SignalManager()
        mgr.install()
        try:
            # Call cancel even though no alarm was set — should not raise.
            mgr.cancel_alarm()
            mgr.cancel_alarm()
        finally:
            mgr.restore()

    def test_set_alarm_exact_integer_second(self):
        from pytest_vigil.infrastructure.enforcement.signals import SignalManager
        mgr = SignalManager()
        mgr.install()
        try:
            mgr.set_alarm(3.0)   # exact integer → ceil(3.0) = 3
            remaining = signal.alarm(0)
            assert remaining >= 3
        finally:
            mgr.restore()
