"""
Test stall detection behavior in various scenarios to ensure it doesn't interfere with other features. of pytest-vigil. 
This includes verifying that stall detection works as expected without causing unintended side effects on regular tests, 
timeout tests, memory limit tests, retry tests, and parametrized tests. 
The tests will cover edge cases such as very short and long timeouts, low CPU thresholds, 
and interactions with instant and busy tests.
"""

pytest_plugins = ["pytester"]


class TestStallDetectionNoInterference:
    """Verify stall detection doesn't interfere with other features."""
    
    def test_stall_no_interference_with_regular_tests(self, pytester):
        """Verify stall detection tests don't affect regular tests."""
        pytester.makepyfile("""
            import pytest
            import time

            def test_regular():
                assert True
            
            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_with_stall():
                time.sleep(1.5)
            
            def test_another_regular():
                assert True
        """)
        result = pytester.runpytest()
        
        # One test should fail (stall), two should pass
        result.stdout.fnmatch_lines(["*1 failed*2 passed*"])
        assert result.ret == 1
    
    def test_stall_no_interference_with_timeout_tests(self, pytester):
        """Verify stall detection doesn't interfere with timeout-only tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_timeout_only():
                time.sleep(0.1)
                assert True
            
            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_only():
                time.sleep(1.5)
            
            @pytest.mark.vigil(timeout=2.0, stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_both():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        
        # Two should pass, one should fail (stall)
        result.stdout.fnmatch_lines(["*1 failed*2 passed*"])
        assert result.ret == 1
    
    def test_stall_no_interference_with_memory_tests(self, pytester):
        """Verify stall detection doesn't interfere with memory limit tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=100)
            def test_memory_only():
                time.sleep(0.1)
                assert True
            
            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_stall_only():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        
        # Both should pass
        assert result.ret == 0
    
    def test_stall_no_interference_with_retry_tests(self, pytester):
        """Verify stall detection doesn't interfere with retry-only tests."""
        pytester.makepyfile("""
            import pytest
            import time
            import os

            FILENAME = "retry_test.txt"

            @pytest.mark.vigil(retry=2)
            def test_retry_only():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
            
            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_stall_only():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        
        # Both should pass (retry succeeds, stall doesn't trigger)
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
        assert result.ret == 0
    
    def test_stall_no_interference_with_parametrized_tests(self, pytester):
        """Verify stall detection works with parametrized tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.parametrize("duration", [0.1, 0.2, 0.3])
            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_parametrized(duration):
                time.sleep(duration)
                assert True
        """)
        result = pytester.runpytest()
        
        # All parametrized tests should pass
        result.stdout.fnmatch_lines(["*3 passed*"])
        assert result.ret == 0
