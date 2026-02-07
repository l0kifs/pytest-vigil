"""
Tests for session timeout behavior in CI environment.
- Verify that CI multiplier is applied to session timeout.
"""

pytest_plugins = ["pytester"]


class TestSessionTimeoutCIEnvironment:
    """Test session timeout behavior in CI environment."""
    
    def test_session_timeout_with_ci_multiplier(self, pytester, monkeypatch):
        """Test that CI multiplier is applied to session timeout."""
        # Simulate CI environment
        monkeypatch.setenv("CI", "true")
        
        pytester.makepyfile("""
            import time
            import pytest

            def test_1():
                time.sleep(0.4)

            def test_2():
                time.sleep(0.4)

            def test_3():
                time.sleep(0.4)

            def test_4():
                time.sleep(0.4)
        """)

        # Set timeout to 1 second - in CI with 2x multiplier = 2 seconds
        # Tests take ~1.6 seconds, so with multiplier they should pass
        result = pytester.runpytest("--vigil-session-timeout=1", "-v")
        
        # With CI multiplier (2x), timeout becomes 2s, tests take ~1.6s - should pass
        # Without multiplier, would timeout
        # Note: This test may be flaky depending on system load
        output = result.stdout.str() + result.stderr.str()
        
        # Verify CI multiplier was recognized
        assert "CI multiplier" in output or result.ret == 0
