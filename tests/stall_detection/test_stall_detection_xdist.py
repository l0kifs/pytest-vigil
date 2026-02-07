"""
Test stall detection behavior in pytest-xdist environments.
- Verify that stall detection correctly identifies stalls when running with pytest-xdist.
- Confirm that multiple tests running in parallel with xdist are correctly evaluated for stall violations.
- Ensure that passing tests do not trigger false positives for stall detection when using xdist.
"""


pytest_plugins = ["pytester"]


class TestStallDetectionXDist:
    """Test stall detection with pytest-xdist."""
    
    def test_stall_detection_xdist_basic(self, pytester):
        """Verify that stall detection works correctly in xdist mode."""
        pytester.makepyfile(test_inner_stall_xdist="""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stalled_xdist():
                # Sleeping consumes almost 0 CPU
                time.sleep(1.5)
        """)
        result = pytester.runpytest("-n", "2")
        
        # Check for policy violation output and failure
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_xdist_multiple_tests(self, pytester):
        """Verify stall detection with multiple tests in xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_1():
                time.sleep(1.5)
            
            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_2():
                time.sleep(1.5)
            
            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_pass():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-n", "3")
        
        # Two should fail, one should pass
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_xdist_passing(self, pytester):
        """Verify passing tests work correctly with xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_pass_1():
                time.sleep(0.1)
                assert True
            
            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_pass_2():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-n", "2")
        
        assert result.ret == 0
