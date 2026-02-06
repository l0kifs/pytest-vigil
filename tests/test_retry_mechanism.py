"""
Comprehensive tests for retry mechanism functionality.

Tests cover:
- Proper functioning with all test outcomes (pass, fail, skip, xfail, xpass)
- All available parameters (marker, CLI, env)
- Parameter precedence
- CI environment interaction
- XDist integration
- Edge cases
- Feature interactions
"""

import pytest
import os

pytest_plugins = ["pytester"]


# =============================================================================
# 1. BASIC FUNCTIONALITY TESTS
# =============================================================================

class TestBasicRetryMechanism:
    """Test basic retry mechanism functionality."""
    
    def test_retry_mechanism_marker(self, pytester):
        """Verify that flaky tests are retried with marker parameter."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "flaky_marker.txt"

            @pytest.mark.vigil(retry=2)
            def test_flaky():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First run fails"
                else:
                    assert True
        """)
        
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Detected Flaky Tests (Passed on Retry):*",
            "*test_flaky*"
        ])
        assert result.ret == 0
    
    def test_retry_mechanism_cli(self, pytester):
        """Verify retry works with CLI parameter."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "flaky_cli.txt"

            @pytest.mark.vigil(timeout=2.0)
            def test_flaky_cli():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First run fails"
                else:
                    assert True
        """)
        
        result = pytester.runpytest("--vigil-retry=2")
        
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
        assert result.ret == 0
    
    def test_retry_mechanism_env(self, pytester, monkeypatch):
        """Verify retry works with environment variable."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "flaky_env.txt"

            @pytest.mark.vigil(timeout=2.0)
            def test_flaky_env():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First run fails"
                else:
                    assert True
        """)
        
        monkeypatch.setenv("PYTEST_VIGIL__RETRY_COUNT", "2")
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
        assert result.ret == 0
    
    def test_no_retry_by_default(self, pytester):
        """Verify tests are not retried by default."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(timeout=2.0)
            def test_fail():
                assert False, "This should fail"
        """)
        
        result = pytester.runpytest()
        
        # Should fail without retry
        assert result.ret == 1
        # Should NOT show flaky test message
        assert "Detected Flaky Tests" not in result.stdout.str()
    
    def test_retry_zero(self, pytester):
        """Verify retry=0 disables retry mechanism."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "no_retry.txt"

            @pytest.mark.vigil(retry=0)
            def test_no_retry():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "Should fail"
                assert True
        """)
        
        result = pytester.runpytest()
        
        # Should fail without retry
        assert result.ret == 1
        assert "Detected Flaky Tests" not in result.stdout.str()


# =============================================================================
# 2. TEST OUTCOMES
# =============================================================================

class TestRetryWithOutcomes:
    """Test retry with all pytest test outcomes."""
    
    def test_retry_with_failing_test(self, pytester):
        """Verify retry with test that eventually passes."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "fail_pass.txt"

            @pytest.mark.vigil(retry=2)
            def test_fail_then_pass():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First attempt fails"
                else:
                    assert True
        """)
        
        result = pytester.runpytest()
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
    
    def test_retry_with_passing_test(self, pytester):
        """Verify passing test with retry doesn't retry."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(retry=2)
            def test_always_pass():
                assert True
        """)
        
        result = pytester.runpytest()
        assert result.ret == 0
        # Should NOT show flaky test message (didn't need retry)
        assert "Detected Flaky Tests" not in result.stdout.str()
    
    def test_retry_with_skipped_test(self, pytester):
        """Verify skipped test is not retried."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(retry=2)
            @pytest.mark.skip(reason="Testing skip")
            def test_skip():
                assert False, "Should never run"
        """)
        
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_skip SKIPPED*"])
        assert result.ret == 0
        # Skipped tests should not be retried
        assert "Detected Flaky Tests" not in result.stdout.str()
    
    def test_retry_with_xfail_test(self, pytester):
        """Verify xfail test is not retried."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(retry=2)
            @pytest.mark.xfail(reason="Expected failure")
            def test_xfail():
                assert False
        """)
        
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_xfail*"])
        assert result.ret == 0
        # xfail tests should not be retried
        assert "Detected Flaky Tests" not in result.stdout.str()
    
    def test_retry_with_xpass_test(self, pytester):
        """Verify xpass test is not retried."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(retry=2)
            @pytest.mark.xfail(reason="Expected failure but passes")
            def test_xpass():
                assert True
        """)
        
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_xpass*"])
        assert result.ret == 0
        # xpass tests should not be retried
        assert "Detected Flaky Tests" not in result.stdout.str()


# =============================================================================
# 3. PARAMETERS AND PRECEDENCE
# =============================================================================

class TestRetryParameters:
    """Test retry parameter precedence and configuration."""
    
    def test_parameter_precedence_marker_over_cli(self, pytester):
        """Verify marker parameter overrides CLI parameter."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "precedence.txt"

            @pytest.mark.vigil(retry=3)
            def test_precedence():
                # Will use marker retry=3, not CLI retry=1
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
        
        # CLI says retry=1, but marker says retry=3
        result = pytester.runpytest("--vigil-retry=1")
        assert result.ret == 0  # Would fail with only 1 retry
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
    
    def test_parameter_precedence_cli_over_env(self, pytester, monkeypatch):
        """Verify CLI parameter overrides environment variable."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "cli_over_env.txt"

            @pytest.mark.vigil(timeout=2.0)
            def test_cli_over_env():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        
        # Env says retry=0, but CLI says retry=2
        monkeypatch.setenv("PYTEST_VIGIL__RETRY_COUNT", "0")
        result = pytester.runpytest("--vigil-retry=2")
        
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])


# =============================================================================
# 4. RESOURCE LIMITS INTERACTION
# =============================================================================

class TestRetryWithLimits:
    """Test retry mechanism with resource limits."""
    
    def test_retry_with_timeout(self, pytester):
        """Verify retry mechanism works with timeout."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "retry_timeout.txt"

            @pytest.mark.vigil(timeout=2.0, retry=2)
            def test_retry_timeout():
                time.sleep(0.1)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First run fails"
                else:
                    assert True
        """)
        result = pytester.runpytest()
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
        assert result.ret == 0

    def test_retry_with_memory(self, pytester):
        """Verify retry mechanism works with memory limits."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "retry_memory.txt"

            @pytest.mark.vigil(memory=200, retry=2)
            def test_retry_memory():
                data = ["x" * 1024 for _ in range(10)]
                time.sleep(0.1)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_retry_with_cpu(self, pytester):
        """Verify retry mechanism works with CPU limits."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "retry_cpu.txt"

            @pytest.mark.vigil(cpu=200, retry=2)
            def test_retry_cpu():
                time.sleep(0.1)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_retry_with_stall_detection(self, pytester):
        """Verify retry works with stall detection."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "retry_stall.txt"

            @pytest.mark.vigil(stall_timeout=2.0, retry=2)
            def test_retry_stall():
                time.sleep(0.1)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0


# =============================================================================
# 5. CI ENVIRONMENT
# =============================================================================

class TestRetryCIEnvironment:
    """Test retry behavior in CI environment."""
    
    def test_retry_count_not_multiplied_in_ci(self, pytester, monkeypatch):
        """Verify retry count is NOT multiplied in CI (unlike timeouts)."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "ci_retry.txt"

            @pytest.mark.vigil(timeout=1.0, retry=1)
            def test_ci_retry():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        
        # Set CI environment
        monkeypatch.setenv("CI", "true")
        result = pytester.runpytest()
        
        # Should pass with retry=1 (not multiplied by ci_multiplier=2.0)
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
    
    def test_retry_with_ci_and_timeout_multiplier(self, pytester, monkeypatch):
        """Verify retry works alongside CI timeout multiplier."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "ci_timeout_retry.txt"

            @pytest.mark.vigil(timeout=1.0, retry=2)
            def test_ci_timeout_retry():
                time.sleep(0.5)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        
        monkeypatch.setenv("CI", "true")
        result = pytester.runpytest()
        
        # Timeout should be multiplied to 2.0s, retry should work
        assert result.ret == 0


# =============================================================================
# 6. XDIST INTEGRATION
# =============================================================================

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


# =============================================================================
# 7. EDGE CASES
# =============================================================================

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


# =============================================================================
# 8. NON-INTERFERENCE
# =============================================================================

class TestRetryNonInterference:
    """Test that retry doesn't interfere with other features."""
    
    def test_retry_with_session_timeout(self, pytester):
        """Verify retry works alongside session timeout."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "session_retry.txt"

            @pytest.mark.vigil(retry=2)
            def test_with_session_timeout():
                time.sleep(0.1)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                assert True
        """)
        
        result = pytester.runpytest("--vigil-session-timeout=10")
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
    
    def test_retry_doesnt_affect_other_tests(self, pytester):
        """Verify retry on one test doesn't affect others."""
        pytester.makepyfile("""
            import pytest
            import os

            @pytest.mark.vigil(retry=2)
            def test_with_retry():
                fname = "with_retry.txt"
                if not os.path.exists(fname):
                    with open(fname, "w") as f:
                        f.write("1")
                    assert False
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_without_retry():
                # This should fail immediately
                assert False, "No retry"
        """)
        
        result = pytester.runpytest()
        
        # One test should pass (with retry), one should fail (no retry)
        assert result.ret == 1
        
        output = result.stdout.str()
        assert "test_with_retry" in output
        assert "test_without_retry" in output
        
        # Check the flaky tests list specifically
        assert "Detected Flaky Tests (Passed on Retry):" in output
        # Extract the flaky tests section - between the header and the table
        flaky_start = output.find("Detected Flaky Tests (Passed on Retry):")
        table_start = output.find("Test ID", flaky_start)
        flaky_list_section = output[flaky_start:table_start]
        
        # Only test_with_retry should be in the flaky list
        assert "test_with_retry" in flaky_list_section
        assert "test_without_retry" not in flaky_list_section

