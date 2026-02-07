"""
Test edge cases for the retry mechanism in pytest-vigil.
This includes scenarios such as exhausting all retry attempts, passing on the last attempt, 
handling multiple flaky tests, using a high retry count, encountering timeouts on retry attempts, 
and dealing with different failure reasons across retries.
"""

pytest_plugins = ["pytester"]


class TestRetryEdgeCases:
    """Test edge cases for retry mechanism."""
    
    def test_retry_exhausted_all_attempts(self, pytester):
        """Verify test fails after exhausting all retry attempts."""
        pytester.makepyfile("""
            import pytest

            attempt_count = 0

            @pytest.mark.vigil(retry=2)
            def test_always_fail():
                assert False, "Always fails"
        """)
        
        result = pytester.runpytest()
        
        # Should fail after 3 attempts (initial + 2 retries)
        assert result.ret == 1
        assert "Detected Flaky Tests" not in result.stdout.str()
    
    def test_retry_passes_last_attempt(self, pytester):
        """Verify test passes on the final retry attempt."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "last_attempt.txt"

            @pytest.mark.vigil(retry=2)
            def test_pass_last():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                elif os.path.getsize(FILENAME) < 2:
                    with open(FILENAME, "a") as f:
                        f.write("2")
                    assert False
                else:
                    assert True
        """)
        
        result = pytester.runpytest()
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
    
    def test_retry_multiple_flaky_tests(self, pytester):
        """Verify multiple flaky tests in one run."""
        pytester.makepyfile("""
            import pytest
            import os

            @pytest.mark.vigil(retry=2)
            def test_flaky_1():
                fname = "flaky_multi_1.txt"
                if not os.path.exists(fname):
                    with open(fname, "w") as f:
                        f.write("1")
                    assert False
                assert True

            @pytest.mark.vigil(retry=2)
            def test_flaky_2():
                fname = "flaky_multi_2.txt"
                if not os.path.exists(fname):
                    with open(fname, "w") as f:
                        f.write("1")
                    assert False
                assert True

            @pytest.mark.vigil(retry=2)
            def test_flaky_3():
                fname = "flaky_multi_3.txt"
                if not os.path.exists(fname):
                    with open(fname, "w") as f:
                        f.write("1")
                    assert False
                assert True
        """)
        
        result = pytester.runpytest()
        assert result.ret == 0
        
        output = result.stdout.str()
        assert "Detected Flaky Tests" in output
        assert "test_flaky_1" in output
        assert "test_flaky_2" in output
        assert "test_flaky_3" in output
    
    def test_retry_high_count(self, pytester):
        """Verify retry works with high retry count."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "high_retry.txt"

            @pytest.mark.vigil(retry=10)
            def test_high_retry():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                assert True
        """)
        
        result = pytester.runpytest()
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
    
    def test_retry_timeout_on_retry_attempt(self, pytester):
        """Verify timeout can occur on retry attempt."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "timeout_retry.txt"

            @pytest.mark.vigil(timeout=0.5, retry=2)
            def test_timeout_on_retry():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    # First attempt: quick fail
                    assert False
                else:
                    # Retry attempt: timeout
                    time.sleep(2.0)
                    assert True
        """)
        
        result = pytester.runpytest()
        
        # Should fail due to timeout on retry
        assert result.ret == 1
        full_output = result.stdout.str() + result.stderr.str()
        assert "TimeoutException" in full_output or "timed out" in full_output.lower()
    
    def test_retry_different_failure_reasons(self, pytester):
        """Verify retry works with different failure reasons."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "diff_failures.txt"

            @pytest.mark.vigil(retry=3)
            def test_different_failures():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    raise ValueError("First failure")
                elif os.path.getsize(FILENAME) < 2:
                    with open(FILENAME, "a") as f:
                        f.write("2")
                    assert 1 == 2, "Second failure"
                elif os.path.getsize(FILENAME) < 3:
                    with open(FILENAME, "a") as f:
                        f.write("3")
                    raise RuntimeError("Third failure")
                else:
                    assert True
        """)
        
        result = pytester.runpytest()
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
