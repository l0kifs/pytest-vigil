import pytest

pytest_plugins = ["pytester"]

def test_stall_detection(pytester):
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

def test_stall_detection_xdist(pytester):
    """
    Verify that stall detection works correctly in xdist mode.
    """
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
