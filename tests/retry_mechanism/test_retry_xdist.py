"""
Tests for retry mechanism with pytest-xdist.
"""

pytest_plugins = ["pytester"]


class TestRetryXDist:
    """Test retry mechanism with pytest-xdist."""
    
    def test_retry_mechanism_xdist(self, pytester):
        """Verify that retry mechanism works correctly in xdist mode."""
        pytester.makepyfile("""
            import pytest
            import os
            
            FILENAME = "flaky_xdist.txt"

            @pytest.mark.vigil(retry=2)
            def test_flaky_xdist():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First run fails"
                else:
                    assert True
        """)
        
        result = pytester.runpytest("-n", "2")
        
        assert result.ret == 0
    
    def test_retry_xdist_multiple_workers(self, pytester):
        """Verify retry works with multiple workers."""
        pytester.makepyfile("""
            import pytest
            import os

            @pytest.mark.vigil(retry=2)
            def test_flaky_1():
                fname = "flaky_1.txt"
                if not os.path.exists(fname):
                    with open(fname, "w") as f:
                        f.write("1")
                    assert False
                assert True

            @pytest.mark.vigil(retry=2)
            def test_flaky_2():
                fname = "flaky_2.txt"
                if not os.path.exists(fname):
                    with open(fname, "w") as f:
                        f.write("1")
                    assert False
                assert True
        """)

        result = pytester.runpytest("-n", "4")
        assert result.ret == 0


class TestRetryWithTimeoutXdist:
    """Retry + timeout combinations must never crash an xdist worker.

    TimeoutException is a BaseException subclass.  The retry loop must catch it
    per-attempt (not let it escape) so the xdist worker stays alive through all
    retry attempts and reports a normal FAILED result rather than INTERNALERROR.
    """

    def test_timeout_on_all_retry_attempts_fails_cleanly(self, pytester):
        """When every retry attempt times out, the result is FAILED — not INTERNALERROR."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3, retry=2)
            def test_always_hangs():
                time.sleep(5)
        """)
        result = pytester.runpytest("-n", "2", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "INTERNALERROR>" not in full_output
        assert "Unexpectedly no active workers available" not in full_output
        assert result.ret == 1

    def test_timeout_on_first_attempt_then_passes_on_retry(self, pytester):
        """A test that times out on attempt 1 and passes on attempt 2 is marked flaky."""
        pytester.makepyfile("""
            import pytest
            import time

            _attempt = [0]

            @pytest.mark.vigil(timeout=0.4, retry=1)
            def test_slow_then_fast():
                _attempt[0] += 1
                if _attempt[0] == 1:
                    time.sleep(5)   # first attempt: times out
                # second attempt: completes quickly
                time.sleep(0.05)
        """)
        result = pytester.runpytest("-n", "1", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "INTERNALERROR>" not in full_output
        assert "Unexpectedly no active workers available" not in full_output
        assert result.ret == 0

    def test_worker_continues_after_retried_timeout(self, pytester):
        """The worker must remain alive after a retried timeout and run the next test."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3, retry=1)
            def test_always_hangs():
                time.sleep(5)

            @pytest.mark.vigil(timeout=2.0)
            def test_runs_after_retried_timeout():
                assert True
        """)
        result = pytester.runpytest("-n", "1", "-v")
        full_output = result.stdout.str() + result.stderr.str()
        assert "INTERNALERROR>" not in full_output
        assert "Unexpectedly no active workers available" not in full_output
        result.assert_outcomes(passed=1, failed=1)
