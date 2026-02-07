"""
Test resource limits in edge cases.
"""

pytest_plugins = ["pytester"]


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
