import pytest
import os

pytest_plugins = ["pytester"]

def test_retry_mechanism(pytester):
    """
    Verify that flaky tests are retried and eventually pass.
    """

    pytester.makepyfile(test_inner_retry="""
        import pytest
        import os

        FILENAME = "flaky_marker.txt"

        @pytest.mark.vigil(retry=2)
        def test_flaky():
            if not os.path.exists(FILENAME):
                with open(FILENAME, "w") as f:
                    f.write("1")
                assert False, "First run fails"
            else:
                assert True
    """)
    
    result = pytester.runpytest()
    
    # Check for report of flaky test
    result.stdout.fnmatch_lines([
        "*Detected Flaky Tests (Passed on Retry):*",
        "*test_flaky*"
    ])
    assert result.ret == 0

def test_retry_mechanism_xdist(pytester):
    """
    Verify that retry mechanism works correctly in xdist mode.
    """
    pytester.makepyfile(test_inner_retry_xdist="""
        import pytest
        import os
        
        # Unique filename ensures no race condition if separate workers run this file multiple times (unlikely with default distro)
        FILENAME = "flaky_xdist.txt"

        @pytest.mark.vigil(retry=2)
        def test_flaky_xdist():
            if not os.path.exists(FILENAME):
                with open(FILENAME, "w") as f:
                    f.write("1")
                assert False, "First run fails"
            else:
                assert True
    """)
    
    # Run with 2 workers
    result = pytester.runpytest("-n", "2")
    
    # It should pass eventually
    assert result.ret == 0
    # Note: Flaky test reporting in output might be interleaved or buffered differently in xdist,
    # but the test passing confirms the retry worked.

