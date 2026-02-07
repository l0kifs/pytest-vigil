"""
Test basic stall detection enforcement in pytest-vigil.
- Verify that tests sleeping for longer than the stall timeout with low CPU usage trigger policy violations.
- Verify that tests with high CPU activity do not trigger stall detection.
- Test various stall CPU thresholds (1%, 10%, 100%) to confirm correct behavior
"""

pytest_plugins = ["pytester"]


class TestBasicStallDetection:
    """Test basic stall detection enforcement."""
    
    def test_stall_detection_violation(self, pytester):
        """
        Verify that stall detection works.
        A test sleeping for > stall_timeout with low CPU should fail.
        """
        pytester.makepyfile(test_inner_stall="""
            import pytest
            import time

            # stall_timeout=0.5s, stall_threshold=100% (force violation even if cpu is high)
            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stalled():
                # Sleeping consumes almost 0 CPU
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        # Check for policy violation output
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_passing(self, pytester):
        """Verify that tests with high CPU activity don't trigger stall detection."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=1.0, stall_cpu_threshold=50.0)
            def test_high_cpu():
                # Busy loop to keep CPU high
                start = time.time()
                while time.time() - start < 0.5:
                    _ = sum(range(10000))
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_stall_detection_with_low_threshold(self, pytester):
        """Verify stall detection with low CPU threshold (1%)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=1.0)
            def test_stall_low_threshold():
                # Sleep should trigger since CPU < 1%
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_with_medium_threshold(self, pytester):
        """Verify stall detection with medium CPU threshold (10%)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=10.0)
            def test_stall_medium_threshold():
                # Sleep should trigger since CPU < 10%
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_boundary_just_under_timeout(self, pytester):
        """Verify test passing just under stall timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=1.0, stall_cpu_threshold=100.0)
            def test_just_under():
                # Sleep for 0.9s, just under 1.0s timeout
                time.sleep(0.9)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_stall_detection_boundary_just_over_timeout(self, pytester):
        """Verify test failing just over stall timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_just_over():
                # Sleep for 1.5s, over 0.5s timeout
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
