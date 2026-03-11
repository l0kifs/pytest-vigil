"""
Tests for resource limits functionality with xdist (parallel test execution).
"""

pytest_plugins = ["pytester"]


class TestResourceLimitsXdist:
    """Test resource limits with pytest-xdist parallel execution."""

    def test_xdist_timeout_enforcement(self, pytester):
        """Timeout in a worker is recorded as a normal FAILED test — no INTERNALERROR, no worker crash.

        Regression: before the fix, TimeoutException (a BaseException subclass) escaped
        pytest_runtest_protocol, killed the xdist worker, and produced
        "INTERNALERROR> RuntimeError: Unexpectedly no active workers available".
        """
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_timeout_worker():
                time.sleep(2)

            @pytest.mark.vigil(timeout=2)
            def test_pass_worker():
                time.sleep(0.2)
        """)
        result = pytester.runpytest("-n", "2", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        # The timeout must surface as a normal test failure, not a worker crash.
        # Use "INTERNALERROR>" (with the pytest prefix) to avoid matching the word
        # in test source code printed by pytest on failure.
        assert "INTERNALERROR>" not in full_output
        assert "Unexpectedly no active workers available" not in full_output
        # The timed-out test is reported as FAILED with Vigil's message.
        assert "Test timed out (Vigil)" in full_output
        # The passing sibling test must have completed normally.
        result.assert_outcomes(passed=1, failed=1)

    def test_xdist_timeout_worker_stays_alive_for_subsequent_tests(self, pytester):
        """After a timeout, the worker continues running subsequent tests correctly.

        Regression: the worker used to crash on TimeoutException, so any test
        scheduled after a timeout would never run — producing the
        "no active workers" error.
        """
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_times_out():
                time.sleep(2)

            @pytest.mark.vigil(timeout=2.0)
            def test_runs_after_timeout_1():
                time.sleep(0.05)
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_runs_after_timeout_2():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-n", "2", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "INTERNALERROR>" not in full_output
        assert "Unexpectedly no active workers available" not in full_output
        result.assert_outcomes(passed=2, failed=1)

    def test_xdist_memory_enforcement(self, pytester):
        """Verify memory enforcement works with xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=10)
            def test_memory_worker():
                data = ["x" * 1024 * 1024 for _ in range(20)]
                time.sleep(1)

            @pytest.mark.vigil(memory=150)
            def test_pass_memory_worker():
                data = ["x" * 1024 for _ in range(10)]
                time.sleep(0.2)
        """)
        result = pytester.runpytest("-n", "2", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "Policy violation" in full_output
        assert result.ret == 1

    def test_xdist_cpu_enforcement(self, pytester):
        """Verify CPU enforcement works with xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=1)
            def test_cpu_worker():
                end = time.time() + 2
                while time.time() < end:
                    _ = [i*i for i in range(1000)]

            @pytest.mark.vigil(cpu=200)
            def test_pass_cpu_worker():
                time.sleep(0.2)
        """)
        result = pytester.runpytest("-n", "2", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "Policy violation" in full_output
        assert result.ret == 1

    def test_xdist_parallel_multiple_tests(self, pytester):
        """Verify multiple tests run in parallel with resource limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_w1():
                time.sleep(0.1)

            @pytest.mark.vigil(timeout=1.0)
            def test_w2():
                time.sleep(0.1)
                
            @pytest.mark.vigil(timeout=1.0)
            def test_w3():
                time.sleep(0.1)
                
            @pytest.mark.vigil(timeout=1.0)
            def test_w4():
                time.sleep(0.1)
        """)
        result = pytester.runpytest("-n", "2", "-v")
        result.assert_outcomes(passed=4)

    def test_xdist_worker_isolation(self, pytester):
        """Verify resource limits are isolated per worker."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_worker_a():
                time.sleep(0.2)
                assert True

            @pytest.mark.vigil(timeout=1.0)
            def test_worker_b():
                time.sleep(0.2)
                assert True
        """)
        result = pytester.runpytest("-n", "2")
        assert result.ret == 0


class TestTimeoutExceptionXdistWorkerSafety:
    """Guard against TimeoutException escaping pytest_runtest_protocol in xdist workers.

    TimeoutException is a BaseException subclass.  Before the fix, an ``except Exception``
    handler in the retry loop silently skipped it, letting it propagate uncaught through
    pytest_runtest_protocol into xdist internals, which killed the worker and produced:

        INTERNALERROR> RuntimeError: Unexpectedly no active workers available

    These tests verify the three related failure modes are all handled correctly.
    """

    def test_timeout_reported_as_failed_not_internalerror(self, pytester):
        """TimeoutException must be converted to a FAILED report, never an INTERNALERROR."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_hangs():
                time.sleep(5)
        """)
        result = pytester.runpytest("-n", "1", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "INTERNALERROR>" not in full_output
        assert "Unexpectedly no active workers available" not in full_output
        assert "Test timed out (Vigil)" in full_output
        assert result.ret == 1

    def test_multiple_sequential_timeouts_in_same_worker(self, pytester):
        """A worker that encounters back-to-back timeouts must survive both.

        With one worker (-n 1), both tests run in the same worker process.
        The second timeout must not crash the worker even though the first
        already triggered the TimeoutException path.
        """
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_timeout_first():
                time.sleep(5)

            @pytest.mark.vigil(timeout=0.3)
            def test_timeout_second():
                time.sleep(5)
        """)
        result = pytester.runpytest("-n", "1", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "INTERNALERROR>" not in full_output
        assert "Unexpectedly no active workers available" not in full_output
        result.assert_outcomes(failed=2)

    def test_timeout_with_retry_does_not_crash_worker(self, pytester):
        """TimeoutException during a retried test must be caught per attempt, not bubble up.

        Before the fix the retry loop used ``except Exception``, so
        TimeoutException escaped the loop entirely and crashed the worker.
        """
        pytester.makepyfile("""
            import pytest
            import time

            _attempt = [0]

            @pytest.mark.vigil(timeout=0.3, retry=1)
            def test_retried_timeout():
                _attempt[0] += 1
                # Both attempts hang — the test must end up FAILED, not cause INTERNALERROR.
                time.sleep(5)
        """)
        result = pytester.runpytest("-n", "1", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "INTERNALERROR>" not in full_output
        assert "Unexpectedly no active workers available" not in full_output
        assert result.ret == 1

    def test_timeout_then_passing_test_in_same_worker(self, pytester):
        """After a timeout, the same worker must execute the next test normally.

        This directly reproduces the "no active workers available" scenario:
        a crash on timeout prevents any subsequent test from running.
        """
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_times_out():
                time.sleep(5)

            @pytest.mark.vigil(timeout=2.0)
            def test_must_still_run():
                # If the worker crashed, this test would never execute.
                assert True
        """)
        result = pytester.runpytest("-n", "1", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "INTERNALERROR>" not in full_output
        assert "Unexpectedly no active workers available" not in full_output
        result.assert_outcomes(passed=1, failed=1)

    def test_exit_code_is_1_not_internalerror_code(self, pytester):
        """A timeout in an xdist worker must exit with code 1 (FAILED), not 3 (INTERNALERROR)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_slow():
                time.sleep(5)
        """)
        result = pytester.runpytest("-n", "2", "-v")
        # pytest exit code 3 = INTERNALERROR; 1 = tests failed normally
        assert result.ret == 1
