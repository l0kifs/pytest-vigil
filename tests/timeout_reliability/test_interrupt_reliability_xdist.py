"""
Tests for all four Interrupt Reliability features with xdist (parallel execution).

In xdist mode each worker is a separate subprocess.  The four reliability
mechanisms must operate correctly in this context:

1. Signal alarm backstop  — SIGALRM is process-local; each worker manages its
   own alarm without interfering with sibling workers.
2. Monitor stop responsiveness — each worker runs its own monitoring thread;
   stop() must be fast and side-effect-free per worker.
3. Force-exit escalation — os._exit(124) fires inside a worker subprocess, not
   in the xdist controller.  The controller handles the crash and exits non-zero,
   but NOT with exit code 124.
4. Faulthandler diagnostics — each worker arms and cancels its own faulthandler
   timer independently; no cross-worker contamination.
"""

import pytest

pytest_plugins = ["pytester"]

# os._exit(124) exit code used by the force-exit escalation path.
# When xdist detects a crashed worker this code is NOT propagated to the
# controller process, so the overall pytest exit code will differ from 124.
_FORCE_EXIT_CODE = 124


# ---------------------------------------------------------------------------
# 1. Signal alarm backstop
# ---------------------------------------------------------------------------

class TestSignalAlarmBackstopXdist:
    """SIGALRM backstop enforcement works correctly across xdist workers."""

    def test_timeout_enforced_in_parallel_workers(self, pytester):
        """Timeout fires independently in each worker."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_slow_a():
                time.sleep(2)

            @pytest.mark.vigil(timeout=0.5)
            def test_slow_b():
                time.sleep(2)

            @pytest.mark.vigil(timeout=2.0)
            def test_fast():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "Test timed out (Vigil)" in full_output
        assert result.ret == 1

    def test_alarm_isolation_between_workers(self, pytester):
        """A stray alarm from worker A does not interrupt a passing test in worker B."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_times_out():
                time.sleep(2)

            @pytest.mark.vigil(timeout=2.0)
            def test_passes():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "-v")
        result.assert_outcomes(passed=1, failed=1)

    def test_alarm_cancelled_per_worker_no_leakage(self, pytester):
        """Each worker cancels its alarm after a timeout; later tests in that worker pass."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_first_times_out():
                time.sleep(2)

            @pytest.mark.vigil(timeout=2.0)
            def test_second_passes():
                time.sleep(0.05)
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_third_passes():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "-v")
        result.assert_outcomes(passed=2, failed=1)

    def test_multiple_timeouts_distributed_across_workers(self, pytester):
        """All slow tests time out correctly when distributed across workers."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_slow_1():
                time.sleep(2)

            @pytest.mark.vigil(timeout=0.3)
            def test_slow_2():
                time.sleep(2)

            @pytest.mark.vigil(timeout=0.3)
            def test_slow_3():
                time.sleep(2)

            @pytest.mark.vigil(timeout=0.3)
            def test_slow_4():
                time.sleep(2)
        """)
        result = pytester.runpytest("-n", "2", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "Test timed out (Vigil)" in full_output
        assert result.ret == 1

    def test_passing_tests_unaffected_in_parallel(self, pytester):
        """Tests that finish before their timeout all pass when run in parallel."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_w1():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=2.0)
            def test_w2():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=2.0)
            def test_w3():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=2.0)
            def test_w4():
                time.sleep(0.05)
        """)
        result = pytester.runpytest("-n", "2", "-v")
        result.assert_outcomes(passed=4)

    def test_alarm_reset_between_retries_in_xdist(self, pytester):
        """Each retry attempt gets a fresh alarm even when tests are distributed via xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            _attempt = [0]

            @pytest.mark.vigil(timeout=1.0, retry=2)
            def test_flaky():
                _attempt[0] += 1
                if _attempt[0] < 3:
                    raise AssertionError("not yet")
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "-v")
        assert result.ret == 0


# ---------------------------------------------------------------------------
# 2. Monitor stop responsiveness
# ---------------------------------------------------------------------------

class TestMonitorStopResponsivenessXdist:
    """VigilMonitor start/stop cycle is correct in each xdist worker."""

    def test_violations_detected_in_multiple_workers(self, pytester):
        """Timeout violations are detected in multiple workers independently."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.4)
            def test_slow_worker_a():
                time.sleep(2)

            @pytest.mark.vigil(timeout=0.4)
            def test_slow_worker_b():
                time.sleep(2)
        """)
        result = pytester.runpytest("-n", "2", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "Test timed out (Vigil)" in full_output
        assert result.ret == 1

    def test_no_monitor_thread_leaks_across_workers(self, pytester):
        """Monitors are correctly started and stopped per test across all workers."""
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

            @pytest.mark.vigil(timeout=1.0)
            def test_d():
                time.sleep(0.05)
        """)
        result = pytester.runpytest("-n", "2", "-v")
        result.assert_outcomes(passed=4)

    def test_monitor_stop_after_violation_in_xdist(self, pytester):
        """After a violation is enforced the monitor stops cleanly; the next test passes."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_times_out():
                time.sleep(2)

            @pytest.mark.vigil(timeout=2.0)
            def test_passes_after():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "-v")
        result.assert_outcomes(passed=1, failed=1)

    def test_many_sequential_tests_per_worker(self, pytester):
        """Many tests running sequentially within workers do not leave monitor debris."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_seq_1():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_seq_2():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_seq_3():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_seq_4():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_seq_5():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_seq_6():
                time.sleep(0.05)
        """)
        result = pytester.runpytest("-n", "3", "-v")
        result.assert_outcomes(passed=6)

    def test_violation_then_pass_mix_in_xdist(self, pytester):
        """A mix of passing and failing tests across workers all resolves correctly."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_fail_1():
                time.sleep(2)

            @pytest.mark.vigil(timeout=0.3)
            def test_fail_2():
                time.sleep(2)

            @pytest.mark.vigil(timeout=2.0)
            def test_pass_1():
                time.sleep(0.05)
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_pass_2():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "-v")
        result.assert_outcomes(passed=2, failed=2)


# ---------------------------------------------------------------------------
# 3. Force-exit escalation
# ---------------------------------------------------------------------------

class TestForceExitEscalationXdist:
    """Force-exit escalation behaviour with xdist workers.

    When --vigil-force-exit-delay is set and a worker calls os._exit(124),
    the xdist controller detects the crashed worker and marks the affected
    test as an error.  The overall pytest exit code is non-zero but NOT 124.
    """

    def test_worker_force_exit_does_not_propagate_124_to_controller(self, pytester):
        """os._exit(124) in a worker is contained; the controller exits non-zero but != 124."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_swallows():
                while True:
                    try:
                        time.sleep(0.01)
                    except BaseException:
                        pass
        """)
        result = pytester.runpytest("-n", "2", "--vigil-force-exit-delay=1.0")
        assert result.ret != 0
        assert result.ret != _FORCE_EXIT_CODE

    def test_sibling_worker_passes_when_one_worker_force_exits(self, pytester):
        """A passing test in another worker completes normally after a sibling force-exits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_swallows():
                while True:
                    try:
                        time.sleep(0.01)
                    except BaseException:
                        pass

            @pytest.mark.vigil(timeout=3.0)
            def test_sibling_passes():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "--vigil-force-exit-delay=1.0")
        full_output = result.stdout.str() + result.stderr.str()
        assert "test_sibling_passes" in full_output
        assert result.ret != 0
        assert result.ret != _FORCE_EXIT_CODE

    def test_no_force_exit_when_disabled_with_xdist(self, pytester):
        """Without --vigil-force-exit-delay, normal soft-interrupt failures occur in workers."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_slow_1():
                time.sleep(2)

            @pytest.mark.vigil(timeout=0.3)
            def test_slow_2():
                time.sleep(2)
        """)
        result = pytester.runpytest("-n", "2")
        # Soft interrupt fires; tests fail with exit code 1, NOT 124.
        assert result.ret == 1
        assert result.ret != _FORCE_EXIT_CODE

    def test_passing_tests_not_escalated_in_xdist(self, pytester):
        """All-passing tests are never escalated even when force-exit-delay is set."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass_a():
                time.sleep(0.05)
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_pass_b():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "--vigil-force-exit-delay=0.5")
        result.assert_outcomes(passed=2)
        assert result.ret != _FORCE_EXIT_CODE

    def test_normal_timeout_failure_in_xdist_is_not_force_exit(self, pytester):
        """Tests that time out via the soft-interrupt path fail with exit code 1, not 124."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_normal_timeout():
                time.sleep(2)
        """)
        # force_exit_delay is long (5 s) — soft interrupt fires first.
        result = pytester.runpytest("-n", "2", "--vigil-force-exit-delay=5.0")
        assert result.ret == 1
        assert result.ret != _FORCE_EXIT_CODE


# ---------------------------------------------------------------------------
# 4. Faulthandler diagnostics
# ---------------------------------------------------------------------------

class TestFaulthandlerDiagnosticsXdist:
    """Faulthandler timers are armed and cancelled independently per xdist worker."""

    def test_faulthandler_does_not_interfere_with_parallel_passing_tests(self, pytester):
        """Multiple tests with timeouts complete correctly in parallel workers."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_quick_a():
                time.sleep(0.05)
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_quick_b():
                time.sleep(0.05)
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_quick_c():
                time.sleep(0.05)
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_quick_d():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "-v")
        result.assert_outcomes(passed=4)

    def test_faulthandler_cancelled_across_workers(self, pytester):
        """Faulthandler from a timed-out test does not fire into subsequent tests in xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_times_out():
                time.sleep(2)

            @pytest.mark.vigil(timeout=2.0)
            def test_passes_1():
                time.sleep(0.05)
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_passes_2():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "-v")
        result.assert_outcomes(passed=2, failed=1)

    def test_no_faulthandler_for_memory_cpu_only_tests_in_xdist(self, pytester):
        """Tests with only memory/CPU limits do not arm faulthandler in any worker."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=999)
            def test_memory_only_a():
                time.sleep(0.05)
                assert True

            @pytest.mark.vigil(memory=999)
            def test_memory_only_b():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "-v")
        result.assert_outcomes(passed=2)

    def test_faulthandler_no_cross_contamination_under_high_parallelism(self, pytester):
        """Faulthandler timers are fully independent across many parallel workers."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_w1():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_w2():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_w3():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_w4():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_w5():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_w6():
                time.sleep(0.05)
        """)
        result = pytester.runpytest("-n", "3", "-v")
        result.assert_outcomes(passed=6)

    def test_faulthandler_retry_cancellation_in_xdist(self, pytester):
        """Faulthandler is cancelled between retries in xdist workers; retried tests pass."""
        pytester.makepyfile("""
            import pytest
            import time

            _attempt_a = [0]
            _attempt_b = [0]

            @pytest.mark.vigil(timeout=1.0, retry=1)
            def test_flaky_a():
                _attempt_a[0] += 1
                if _attempt_a[0] < 2:
                    raise AssertionError("first attempt fails")
                time.sleep(0.05)
                assert True

            @pytest.mark.vigil(timeout=1.0, retry=1)
            def test_flaky_b():
                _attempt_b[0] += 1
                if _attempt_b[0] < 2:
                    raise AssertionError("first attempt fails")
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "-v")
        assert result.ret == 0
