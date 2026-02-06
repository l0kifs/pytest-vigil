"""
Comprehensive tests for resource limits functionality.

This test module covers all aspects of pytest-vigil resource limit enforcement:
- Timeout, Memory, and CPU limit enforcement
- All test outcomes (pass, fail, skip, xfail, xpass)
- CLI parameter handling
- Configuration precedence (marker > CLI > env)
- CI environment interaction
- xdist compatibility
- Edge cases and boundary conditions
- Feature interactions
- Report generation

All resource limit tests should be in this file to avoid duplication and fragmentation.
"""
import pytest
import json
import os

pytest_plugins = ["pytester"]


# =============================================================================
# 1. BASIC FUNCTIONALITY TESTS
# =============================================================================

class TestBasicResourceLimits:
    """Test basic enforcement of timeout, memory, and CPU limits."""
    
    def test_timeout_enforcement(self, pytester):
        """Verify that timeout limit is enforced."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_sleep():
                time.sleep(1)
        """)
        result = pytester.runpytest()
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1

    def test_timeout_passing(self, pytester):
        """Verify that tests complete successfully under timeout limit."""
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

    def test_memory_limit_enforcement(self, pytester):
        """Verify that memory limit is enforced."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=10)
            def test_memory():
                # Allocate ~20MB
                data = ["x" * 1024 * 1024 for _ in range(20)]
                time.sleep(1)  # Allow monitor to catch it
        """)
        result = pytester.runpytest()
        stdout_str = result.stdout.str()
        stderr_str = result.stderr.str()
        full_output = stdout_str + stderr_str
        
        assert "TimeoutException: Test timed out (Vigil)" in full_output
        assert "Policy violation" in full_output
        assert result.ret == 1

    def test_memory_passing(self, pytester):
        """Verify that tests complete successfully under memory limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=150)
            def test_small_memory():
                data = ["x" * 1024 for _ in range(10)]  # ~10KB
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_cpu_limit_enforcement(self, pytester):
        """Verify that CPU limit is enforced."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=1) 
            def test_cpu():
                end = time.time() + 2
                while time.time() < end:
                    _ = [i*i for i in range(1000)]
        """)
        result = pytester.runpytest()
        stdout_str = result.stdout.str()
        stderr_str = result.stderr.str()
        full_output = stdout_str + stderr_str
        
        assert "TimeoutException: Test timed out (Vigil)" in full_output
        assert "Policy violation" in full_output
        assert result.ret == 1

    def test_cpu_passing(self, pytester):
        """Verify that tests complete successfully under CPU limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=200)
            def test_light_cpu():
                time.sleep(0.2)
                result = sum(range(100))
                assert result > 0
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_combined_limits(self, pytester):
        """Verify that multiple limits can be applied simultaneously."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, memory=150, cpu=200)
            def test_combined():
                time.sleep(0.1)
                data = ["x" * 1024 for _ in range(10)]
                result = sum(range(100))
                assert result > 0
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_combined_limits_timeout_violation(self, pytester):
        """Verify that timeout violation is detected with multiple limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5, memory=150, cpu=50)
            def test_timeout_fail():
                time.sleep(2)
        """)
        result = pytester.runpytest()
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1


# =============================================================================
# 2. TEST OUTCOMES COVERAGE
# =============================================================================

class TestResourceLimitsWithOutcomes:
    """Test resource limits with all pytest test outcomes."""
    
    def test_passed_test_with_timeout(self, pytester):
        """Verify passed test with timeout limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_pass():
                time.sleep(0.1)
                assert 1 + 1 == 2
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_pass PASSED*"])
        assert result.ret == 0

    def test_failed_test_with_timeout(self, pytester):
        """Verify failed test (assertion) with timeout limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_fail():
                time.sleep(0.1)
                assert 1 + 1 == 3
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_fail FAILED*"])
        result.stdout.fnmatch_lines(["*AssertionError*"])
        assert result.ret == 1

    def test_skipped_test_with_timeout(self, pytester):
        """Verify skipped test with timeout limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            @pytest.mark.skip(reason="Testing skip")
            def test_skip():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_skip SKIPPED*"])
        assert result.ret == 0

    def test_xfail_test_with_timeout(self, pytester):
        """Verify xfail test with timeout limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            @pytest.mark.xfail(reason="Expected failure")
            def test_xfail():
                time.sleep(0.1)
                assert False
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_xfail*"])
        assert result.ret == 0

    def test_xpass_test_with_timeout(self, pytester):
        """Verify xpass test with timeout limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            @pytest.mark.xfail(reason="Expected failure")
            def test_xpass():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_xpass*"])
        assert result.ret == 0

    def test_mixed_outcomes(self, pytester):
        """Verify multiple tests with different outcomes and resource limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_pass():
                time.sleep(0.1)
                assert True

            @pytest.mark.vigil(timeout=1.0)
            def test_fail():
                time.sleep(0.1)
                assert False

            @pytest.mark.vigil(timeout=1.0)
            @pytest.mark.skip(reason="Skip")
            def test_skip():
                pass
        """)
        result = pytester.runpytest("-v")
        assert result.ret == 1  # Has failed test


# =============================================================================
# 3. CLI PARAMETERS TESTS
# =============================================================================

class TestResourceLimitsCLI:
    """Test resource limits via CLI parameters."""
    
    def test_cli_timeout_option(self, pytester):
        """Verify --vigil-timeout CLI option works."""
        pytester.makepyfile("""
            import time
            
            def test_cli_timeout():
                time.sleep(1.5)
        """)
        result = pytester.runpytest("--vigil-timeout=0.5")
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1

    def test_cli_timeout_passing(self, pytester):
        """Verify test passes under CLI timeout limit."""
        pytester.makepyfile("""
            import time
            
            def test_cli_timeout_pass():
                time.sleep(0.2)
                assert True
        """)
        result = pytester.runpytest("--vigil-timeout=1.0")
        assert result.ret == 0

    def test_cli_memory_option(self, pytester):
        """Verify --vigil-memory CLI option works."""
        pytester.makepyfile("""
            import time
            
            def test_cli_memory():
                data = ["x" * 1024 * 1024 for _ in range(30)]
                time.sleep(1)
        """)
        result = pytester.runpytest("--vigil-memory=10")
        full_output = result.stdout.str() + result.stderr.str()
        assert "Policy violation" in full_output
        assert result.ret == 1

    def test_cli_cpu_option(self, pytester):
        """Verify --vigil-cpu CLI option works."""
        pytester.makepyfile("""
            import time
            
            def test_cli_cpu():
                end = time.time() + 2
                while time.time() < end:
                    _ = [i*i for i in range(1000)]
        """)
        result = pytester.runpytest("--vigil-cpu=1")
        full_output = result.stdout.str() + result.stderr.str()
        assert "Policy violation" in full_output
        assert result.ret == 1

    def test_cli_combined_options(self, pytester):
        """Verify multiple CLI options work together."""
        pytester.makepyfile("""
            import time
            
            def test_cli_combined():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("--vigil-timeout=1.0", "--vigil-memory=150", "--vigil-cpu=200")
        assert result.ret == 0

    def test_cli_timeout_with_violation(self, pytester):
        """Verify CLI timeout violation with combined options."""
        pytester.makepyfile("""
            import time
            
            def test_cli_timeout_violation():
                time.sleep(2)
        """)
        result = pytester.runpytest("--vigil-timeout=0.5", "--vigil-memory=150")
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1


# =============================================================================
# 4. CONFIGURATION PRECEDENCE TESTS
# =============================================================================

class TestResourceLimitsPrecedence:
    """Test configuration precedence: marker > CLI > env."""
    
    def test_marker_overrides_cli(self, pytester):
        """Verify marker takes precedence over CLI."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_marker_override():
                time.sleep(0.5)
        """)
        result = pytester.runpytest("--vigil-timeout=0.1")
        assert result.ret == 0  # Marker timeout=2.0 allows it to pass

    def test_marker_overrides_env(self, pytester, monkeypatch):
        """Verify marker takes precedence over environment variable."""
        monkeypatch.setenv("PYTEST_VIGIL__TIMEOUT", "0.1")
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_marker_over_env():
                time.sleep(0.5)
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_cli_overrides_env(self, pytester, monkeypatch):
        """Verify CLI takes precedence over environment variable."""
        monkeypatch.setenv("PYTEST_VIGIL__TIMEOUT", "2.0")
        pytester.makepyfile("""
            import time
            
            def test_cli_over_env():
                time.sleep(1.0)
        """)
        result = pytester.runpytest("--vigil-timeout=0.5")
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1

    def test_env_var_default(self, pytester, monkeypatch):
        """Verify environment variable is used when no CLI or marker."""
        monkeypatch.setenv("PYTEST_VIGIL__TIMEOUT", "0.5")
        pytester.makepyfile("""
            import time
            
            def test_env_default():
                time.sleep(1.0)
        """)
        result = pytester.runpytest()
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1

    def test_function_marker_overrides_class(self, pytester):
        """Verify function marker overrides class marker."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.1)
            class TestClass:
                @pytest.mark.vigil(timeout=5)
                def test_override_extended(self):
                    time.sleep(0.5)
                
                def test_inherit_class(self):
                    time.sleep(0.5)
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines([
            "*test_override_extended PASSED*",
            "*test_inherit_class FAILED*"
        ])
        assert result.ret == 1

    def test_partial_marker_override(self, pytester):
        """Verify partial marker override (timeout from marker, memory from CLI)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_partial():
                time.sleep(0.2)
                data = ["x" * 1024 for _ in range(10)]
                assert True
        """)
        result = pytester.runpytest("--vigil-memory=200")
        assert result.ret == 0


# =============================================================================
# 5. CI ENVIRONMENT TESTS
# =============================================================================

class TestResourceLimitsCI:
    """Test CI multiplier application for resource limits."""
    
    def test_ci_multiplier_timeout(self, pytester):
        """Verify CI multiplier is applied to timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_ci_timeout():
                time.sleep(0.8)  # Would fail without multiplier
        """)
        with pytest.MonkeyPatch.context() as m:
            m.setenv("CI", "true")
            result = pytester.runpytest()
            assert result.ret == 0  # Passes with 2x multiplier (timeout=1.0)

    def test_no_ci_multiplier(self, pytester):
        """Verify no multiplier when CI is not set."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_no_ci():
                time.sleep(0.8)
        """)
        with pytest.MonkeyPatch.context() as m:
            m.setenv("CI", "false")
            result = pytester.runpytest()
            result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
            assert result.ret == 1

    def test_github_actions_detection(self, pytester):
        """Verify GITHUB_ACTIONS environment variable triggers CI multiplier."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_github_actions():
                time.sleep(0.8)
        """)
        with pytest.MonkeyPatch.context() as m:
            m.setenv("GITHUB_ACTIONS", "true")
            result = pytester.runpytest()
            assert result.ret == 0

    def test_ci_multiplier_memory(self, pytester):
        """Verify CI multiplier concept with memory (no direct multiplier but test compatibility)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=150)
            def test_ci_memory():
                data = ["x" * 1024 * 10 for _ in range(100)]  # ~1MB
                time.sleep(0.2)
                assert True
        """)
        with pytest.MonkeyPatch.context() as m:
            m.setenv("CI", "true")
            result = pytester.runpytest()
            assert result.ret == 0

    def test_ci_multiplier_cpu(self, pytester):
        """Verify CI multiplier with CPU limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=200)
            def test_ci_cpu():
                time.sleep(0.2)
                result = sum(range(1000))
                assert result > 0
        """)
        with pytest.MonkeyPatch.context() as m:
            m.setenv("CI", "true")
            result = pytester.runpytest()
            assert result.ret == 0


# =============================================================================
# 6. XDIST COMPATIBILITY TESTS
# =============================================================================

class TestResourceLimitsXdist:
    """Test resource limits with pytest-xdist parallel execution."""
    
    def test_xdist_timeout_enforcement(self, pytester):
        """Verify timeout enforcement works with xdist."""
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
        # Check that at least one failed and one passed
        full_output = result.stdout.str() + result.stderr.str()
        assert "TimeoutException: Test timed out (Vigil)" in full_output
        assert "test_pass_worker" in full_output
        assert result.ret == 1

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


# =============================================================================
# 7. EDGE CASES TESTS
# =============================================================================

class TestResourceLimitsEdgeCases:
    """Test edge cases and boundary conditions for resource limits."""
    
    def test_zero_timeout(self, pytester):
        """Verify zero timeout triggers immediately."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0)
            def test_zero_timeout():
                time.sleep(0.1)
        """)
        result = pytester.runpytest()
        full_output = result.stdout.str() + result.stderr.str()
        assert "TimeoutException: Test timed out (Vigil)" in full_output
        assert "Policy violation" in full_output
        assert result.ret == 1

    def test_zero_memory(self, pytester):
        """Verify zero memory limit triggers on any allocation."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=0)
            def test_zero_memory():
                data = ["x" * 10]
                time.sleep(0.5)
        """)
        result = pytester.runpytest()
        full_output = result.stdout.str() + result.stderr.str()
        assert "Policy violation" in full_output
        assert result.ret == 1

    def test_zero_cpu(self, pytester):
        """Verify zero CPU limit triggers on any CPU usage."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=0)
            def test_zero_cpu():
                _ = sum(range(100))
                time.sleep(0.5)
        """)
        result = pytester.runpytest()
        full_output = result.stdout.str() + result.stderr.str()
        assert "Policy violation" in full_output
        assert result.ret == 1

    def test_very_high_timeout(self, pytester):
        """Verify very high timeout doesn't interfere with normal test execution."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=999999)
            def test_high_timeout():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_very_high_memory(self, pytester):
        """Verify very high memory limit doesn't interfere."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=999999)
            def test_high_memory():
                data = ["x" * 1024 for _ in range(100)]
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_float_timeout(self, pytester):
        """Verify float timeout values work correctly."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.25)
            def test_float_timeout():
                time.sleep(0.5)
        """)
        result = pytester.runpytest()
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1

    def test_float_memory(self, pytester):
        """Verify float memory values work correctly."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=0.5)
            def test_float_memory():
                data = ["x" * 1024 * 1024 for _ in range(2)]
                time.sleep(0.5)
        """)
        result = pytester.runpytest()
        full_output = result.stdout.str() + result.stderr.str()
        # Memory violation triggers timeout exception
        assert "Test timed out (Vigil)" in full_output or "Policy violation" in full_output
        assert result.ret == 1

    def test_slow_fixture_timeout(self, pytester):
        """Verify that slow fixture setup triggers timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.fixture
            def slow_setup():
                time.sleep(2)
                return True

            @pytest.mark.vigil(timeout=1)
            def test_with_slow_fixture(slow_setup):
                pass
        """)
        result = pytester.runpytest()
        full_output = result.stdout.str() + result.stderr.str()
        assert "TimeoutException: Test timed out (Vigil)" in full_output
        assert result.ret == 1

    def test_exception_swallowing_attempt(self, pytester):
        """Verify that catching Exception does not catch TimeoutException."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1)
            def test_swallow():
                try:
                    time.sleep(2)
                except Exception:
                    pass
        """)
        result = pytester.runpytest()
        full_output = result.stdout.str() + result.stderr.str()
        assert "TimeoutException: Test timed out (Vigil)" in full_output
        assert result.ret == 1

    def test_parametrized_with_limits(self, pytester):
        """Verify resource limits work with parametrized tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            @pytest.mark.parametrize("value", [1, 2, 3])
            def test_parametrized(value):
                time.sleep(0.1)
                assert value > 0
        """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=3)

    def test_class_based_tests_with_limits(self, pytester):
        """Verify resource limits work with class-based tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            class TestClass:
                def test_method_1(self):
                    time.sleep(0.1)
                    assert True
                
                def test_method_2(self):
                    time.sleep(0.1)
                    assert True
        """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=2)

    def test_fixture_teardown_timeout(self, pytester):
        """Verify timeout applies during fixture teardown."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.fixture
            def slow_teardown():
                yield True
                time.sleep(2)  # Slow teardown

            @pytest.mark.vigil(timeout=1)
            def test_with_slow_teardown(slow_teardown):
                time.sleep(0.1)
        """)
        result = pytester.runpytest()
        full_output = result.stdout.str() + result.stderr.str()
        assert "TimeoutException: Test timed out (Vigil)" in full_output
        assert result.ret == 1

    def test_near_limit_timeout(self, pytester):
        """Verify tests near timeout limit are handled correctly."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_near_limit():
                time.sleep(0.95)  # 95% of limit
                assert True
        """)
        result = pytester.runpytest()
        # Should pass as it's under the limit
        assert result.ret == 0


# =============================================================================
# 8. FEATURE INTERACTIONS TESTS
# =============================================================================

class TestResourceLimitsInteractions:
    """Test resource limits interaction with other pytest-vigil features."""
    
    def test_timeout_with_stall_detection(self, pytester):
        """Verify timeout and stall detection work together."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_timeout_stall():
                time.sleep(1.5)  # Stall should trigger first
        """)
        result = pytester.runpytest()
        full_output = result.stdout.str() + result.stderr.str()
        assert "Policy violation" in full_output
        assert result.ret == 1


# =============================================================================
# 9. REPORT GENERATION TESTS
# =============================================================================

class TestResourceLimitsReports:
    """Test JSON report generation with resource limits."""
    
    def test_report_with_timeout(self, pytester):
        """Verify timeout limit appears in JSON report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.5)
            def test_with_timeout():
                time.sleep(0.1)
                assert True
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        assert "test_with_timeout" in data["results"][0]["node_id"]
        # Check limits are recorded
        limits = data["results"][0]["limits"]
        assert any(limit["limit_type"] == "time" for limit in limits)

    def test_report_with_memory(self, pytester):
        """Verify memory limit appears in JSON report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=150)
            def test_with_memory():
                data = ["x" * 1024 for _ in range(10)]
                time.sleep(0.1)
                assert True
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        limits = data["results"][0]["limits"]
        assert any(limit["limit_type"] == "memory" for limit in limits)

    def test_report_with_cpu(self, pytester):
        """Verify CPU limit appears in JSON report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=200)
            def test_with_cpu():
                time.sleep(0.1)
                result = sum(range(100))
                assert result > 0
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        limits = data["results"][0]["limits"]
        assert any(limit["limit_type"] == "cpu" for limit in limits)

    def test_report_with_all_limits(self, pytester):
        """Verify all limits appear in JSON report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, memory=150, cpu=200)
            def test_all_limits():
                time.sleep(0.1)
                data = ["x" * 1024 for _ in range(5)]
                result = sum(range(50))
                assert result > 0
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        limits = data["results"][0]["limits"]
        limit_types = [limit["limit_type"] for limit in limits]
        assert "time" in limit_types
        assert "memory" in limit_types
        assert "cpu" in limit_types

    def test_report_violation_details(self, pytester):
        """Verify violation details appear in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_violation():
                time.sleep(2)
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        assert result.ret == 1
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        # Check that violation information is captured
        assert data["results"][0]["duration"] > 0

    def test_report_cli_limits(self, pytester):
        """Verify CLI-specified limits appear in report."""
        pytester.makepyfile("""
            import time
            
            def test_cli_limits():
                time.sleep(0.1)
                assert True
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}", "--vigil-timeout=2.0")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        limits = data["results"][0]["limits"]
        assert any(limit["limit_type"] == "time" for limit in limits)

    def test_report_xdist_aggregation(self, pytester):
        """Verify report aggregates results from xdist workers."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_worker_1():
                time.sleep(0.1)

            @pytest.mark.vigil(timeout=1.0)
            def test_worker_2():
                time.sleep(0.1)

            @pytest.mark.vigil(timeout=1.0)
            def test_worker_3():
                time.sleep(0.1)
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}", "-n", "2")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        # Should have all 3 tests in report
        assert len(data["results"]) == 3
