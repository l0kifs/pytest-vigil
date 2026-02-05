import pytest

pytest_plugins = ["pytester"]

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

def test_marker_overrides_cli(pytester):
    """Verify marker takes precedence over CLI."""
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(timeout=2)
        def test_pass_with_override():
            time.sleep(0.5)
    """)
    result = pytester.runpytest("--vigil-timeout=0.1")
    assert result.ret == 0
