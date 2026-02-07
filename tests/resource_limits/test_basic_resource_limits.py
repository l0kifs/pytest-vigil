"""
Basic tests for resource limits functionality.
"""

pytest_plugins = ["pytester"]


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
