"""
Test stall detection interaction with other pytest-vigil features.
- Verify that stall detection correctly interacts with timeout limits, memory limits, and CPU limits.
- Confirm that stall detection works correctly with the retry mechanism, both when retries fail and when they succeed.
- Ensure that stall detection does not interfere with other features and that policy violations are reported accurately when multiple limits are set.
"""

pytest_plugins = ["pytester"]


class TestStallDetectionFeatureInteraction:
    """Test stall detection interaction with other pytest-vigil features."""
    
    def test_stall_with_timeout_both_pass(self, pytester):
        """Verify stall and timeout limits both pass."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_both_pass():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_stall_with_timeout_stall_triggers_first(self, pytester):
        """Verify stall detection triggers before timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=5.0, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_first():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        # Stall detection (0.5s) should trigger before timeout (5.0s)
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_with_timeout_timeout_triggers_first(self, pytester):
        """Verify timeout triggers before stall detection."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5, stall_timeout=5.0, stall_cpu_threshold=100.0)
            def test_timeout_first():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        # Timeout (0.5s) should trigger before stall detection (5.0s)
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1
    
    def test_stall_with_memory_limit(self, pytester):
        """Verify stall detection works with memory limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=100, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_and_memory():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_with_cpu_limit(self, pytester):
        """Verify stall detection works with CPU limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=200, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_and_cpu():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_with_all_limits(self, pytester):
        """Verify stall detection works with all limit types."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(
                timeout=5.0,
                memory=100,
                cpu=200,
                stall_timeout=0.5,
                stall_cpu_threshold=100.0
            )
            def test_all_limits():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_with_retry_fails_all_attempts(self, pytester):
        """Verify stall detection with retry mechanism - fails all attempts."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(retry=2, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_with_retry_fail():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        # Should fail all retry attempts
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_with_retry_passes_on_retry(self, pytester):
        """Verify stall detection with retry - passes on retry."""
        pytester.makepyfile("""
            import pytest
            import time
            import os

            FILENAME = "stall_retry.txt"

            @pytest.mark.vigil(retry=2, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_retry_success():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    # First attempt stalls
                    time.sleep(1.5)
                else:
                    # Second attempt passes quickly
                    time.sleep(0.1)
                    assert True
        """)
        result = pytester.runpytest()
        
        # Should show flaky test (passed on retry)
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
        assert result.ret == 0
