import pytest

pytest_plugins = ["pytester"]

def test_slow_fixture_timeout(pytester):
    """Verify that a slow fixture setup triggers the timeout."""
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.fixture
        def slow_setup():
            time.sleep(2)
            return True

        @pytest.mark.vigil(timeout=1)
        def test_with_slow_fixture(slow_setup):
            pass
    """)
    result = pytester.runpytest()
    stdout_str = result.stdout.str()
    stderr_str = result.stderr.str()
    full_output = stdout_str + stderr_str
    
    assert "TimeoutException: Test timed out (Vigil)" in full_output
    assert result.ret == 1

def test_exception_swallowing_attempt(pytester):
    """Verify that catching Exception does not catch the configured signal/TimeoutException."""
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(timeout=1)
        def test_swallow():
            try:
                time.sleep(2)
            except Exception:
                pass 
            # Note: TimeoutException should inherit from BaseException, so it bypasses Exception catch
    """)
    result = pytester.runpytest()
    stdout = result.stdout.str()
    # Should still fail
    assert "TimeoutException: Test timed out (Vigil)" in stdout + result.stderr.str()
    assert result.ret == 1

def test_marker_precedence(pytester):
    """Verify that function marker overrides class marker."""
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(timeout=0.1)
        class TestClass:
            @pytest.mark.vigil(timeout=5)
            def test_override_extended(self):
                # Should NOT timeout at 0.1s because function says 5s
                time.sleep(0.5)
            
            def test_inherit_class(self):
                # Should timeout at 0.1s
                time.sleep(0.5)
    """)
    result = pytester.runpytest("-v")
    
    # test_override_extended should PASS (time.sleep(0.5) < 5)
    # test_inherit_class should FAIL (time.sleep(0.5) > 0.1)
    
    result.stdout.fnmatch_lines([
        "*test_override_extended PASSED*",
        "*test_inherit_class FAILED*"
    ])
    assert result.ret == 1
