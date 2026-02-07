"""
Test edge cases and boundary conditions for stall detection.
- Verify stall detection with very short timeout (0.1s).
- Verify stall detection with very long timeout (10s).
- Verify stall detection with very low CPU threshold.
- Verify instant tests don't trigger stall detection.
- Verify busy tests (no sleep) don't trigger stall detection.
- Verify multiple short sleeps below stall timeout.
"""

pytest_plugins = ["pytester"]


class TestStallDetectionEdgeCases:
    """Test edge cases and boundary conditions for stall detection."""
    
    def test_stall_very_short_timeout(self, pytester):
        """Verify stall detection with very short timeout (0.1s)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.1, stall_cpu_threshold=100.0)
            def test_very_short_timeout():
                time.sleep(0.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_very_long_timeout(self, pytester):
        """Verify stall detection with very long timeout (10s)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=10.0, stall_cpu_threshold=100.0)
            def test_very_long_timeout():
                time.sleep(0.5)
                assert True
        """)
        result = pytester.runpytest()
        
        # Should pass as timeout is very long
        assert result.ret == 0
    
    def test_stall_zero_threshold(self, pytester):
        """Verify stall detection with very low CPU threshold."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=5.0)
            def test_zero_threshold():
                # Low threshold should trigger for sleep
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_instant_test(self, pytester):
        """Verify instant tests don't trigger stall detection."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_instant():
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_stall_no_sleep_busy_test(self, pytester):
        """Verify busy tests (no sleep) don't trigger stall detection."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=50.0)
            def test_busy():
                # Busy loop for 1s - high CPU, should not trigger stall
                start = time.time()
                while time.time() - start < 1.0:
                    _ = sum(range(10000))
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_stall_multiple_short_sleeps(self, pytester):
        """Verify multiple short sleeps below stall timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=1.0, stall_cpu_threshold=100.0)
            def test_multiple_short_sleeps():
                # Multiple 0.3s sleeps - each below 1.0s stall timeout
                for _ in range(5):
                    time.sleep(0.3)
        """)
        result = pytester.runpytest()
        
        # May trigger stall detection depending on timing
        # The current implementation checks duration, not individual sleeps
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_without_vigil_marker(self, pytester):
        """Verify tests without vigil marker are not monitored."""
        pytester.makepyfile("""
            import time

            def test_no_vigil():
                time.sleep(2.0)
                assert True
        """)
        result = pytester.runpytest()
        
        # Should pass as no monitoring is enabled
        assert result.ret == 0
    
    def test_stall_empty_test_function(self, pytester):
        """Verify empty test functions don't trigger stall detection."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_empty():
                pass
        """)
        result = pytester.runpytest()
        assert result.ret == 0
