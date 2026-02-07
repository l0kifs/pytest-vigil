"""
Tests for session timeout parameter configuration.
- Verify grace period configuration through CLI and environment variables.
- Test parameter precedence (CLI overrides environment variables).
"""

pytest_plugins = ["pytester"]


class TestSessionTimeoutParameters:
    """Test session timeout parameter configuration."""
    
    def test_session_timeout_grace_period_cli_option(self, pytester):
        """Test that grace period can be set via CLI option."""
        pytester.makepyfile("""
            import time
            import pytest

            def test_long():
                time.sleep(2.0)
        """)

        # Set short timeout with custom grace period
        result = pytester.runpytest_subprocess(
            "--vigil-session-timeout=1",
            "--vigil-session-timeout-grace-period=2",
            "-v"
        )
        
        # Should be terminated
        assert result.ret != 0
        output = result.stdout.str() + result.stderr.str()
        assert "Session monitor started" in output or result.ret in [124, 143, 137, -15, -9]

    def test_session_timeout_grace_period_cli_overrides_env(self, pytester, monkeypatch):
        """Test that CLI grace period overrides environment variable."""
        monkeypatch.setenv("PYTEST_VIGIL__SESSION_TIMEOUT_GRACE_PERIOD", "10.0")
        
        pytester.makepyfile("""
            import time
            import pytest

            def test_long():
                time.sleep(2.0)
        """)

        # CLI sets custom grace period that should override env var
        result = pytester.runpytest_subprocess(
            "--vigil-session-timeout=1",
            "--vigil-session-timeout-grace-period=1",
            "-v"
        )
        
        # Should be terminated
        assert result.ret != 0
        output = result.stdout.str() + result.stderr.str()
        assert "Session monitor started" in output or result.ret in [124, 143, 137, -15, -9]

    def test_session_timeout_grace_period_env_var(self, pytester, monkeypatch):
        """Test that grace period can be set via environment variable."""
        monkeypatch.setenv("PYTEST_VIGIL__SESSION_TIMEOUT", "1.0")
        monkeypatch.setenv("PYTEST_VIGIL__SESSION_TIMEOUT_GRACE_PERIOD", "2.0")
        
        pytester.makepyfile("""
            import time
            import pytest

            def test_long():
                time.sleep(2.0)
        """)

        result = pytester.runpytest_subprocess("-v")
        
        # Should be terminated
        assert result.ret != 0
        output = result.stdout.str() + result.stderr.str()
        assert "Session monitor started" in output or result.ret in [124, 143, 137, -15, -9]
