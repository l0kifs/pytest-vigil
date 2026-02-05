import pytest
import time

pytest_plugins = ["pytester"]

def test_ci_multiplier(pytester, monkeypatch):
    """
    Verify that CI multiplier works.
    Test takes 0.8s. Timeout is 0.5s.
    If CI=true (multiplier=2.0), timeout becomes 1.0s -> Pass.
    If CI=false, timeout 0.5s -> Fail.
    """

    pytester.makepyfile(test_inner_ci="""
        import pytest
        import time

        @pytest.mark.vigil(timeout=0.5)
        def test_ci_slow():
            time.sleep(0.8)
    """)
    
    # Run with CI=true (multiplier=2.0, timeout becomes 1.0s -> Pass)
    with pytest.MonkeyPatch.context() as m:
        m.setenv("CI", "true")
        result = pytester.runpytest()
        assert result.ret == 0

    # Run without CI variable (should fail)
    with pytest.MonkeyPatch.context() as m:
        m.setenv("CI", "false")
        result_fail = pytester.runpytest()
        assert result_fail.ret == 1

def test_ci_multiplier_xdist(pytester):
    """
    Verify that CI multiplier works correctly in xdist mode.
    """
    pytester.makepyfile(test_inner_ci_xdist="""
        import pytest
        import time

        @pytest.mark.vigil(timeout=0.5)
        def test_ci_worker():
            time.sleep(0.8)
    """)
    
    # Run with CI=true and xdist
    with pytest.MonkeyPatch.context() as m:
        m.setenv("CI", "true")
        result = pytester.runpytest("-n", "2")
        assert result.ret == 0
