"""
Tests for resource limits functionality with xdist (parallel test execution).
"""

pytest_plugins = ["pytester"]


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
