"""
Test basic session timeout functionality.
- Verify that session timeout can be set via CLI and environment variable.
- Ensure that session timeout terminates long-running test suites.
- Test that timeout does not interfere when longer than test suite duration.
"""

pytest_plugins = ["pytester"]


class TestBasicSessionTimeout:
    """Test basic session timeout functionality."""
    
    def test_session_timeout_cli_option(self, pytester):
        """Test that session timeout can be set via CLI and terminates long-running test suites."""
        pytester.makepyfile("""
            import time
            import pytest

            def test_long_1():
                time.sleep(0.5)

            def test_long_2():
                time.sleep(0.5)

            def test_long_3():
                time.sleep(0.5)
        """)

        # Set session timeout to 1 second, but tests will take ~1.5 seconds total
        result = pytester.runpytest_subprocess("--vigil-session-timeout=1", "-v")
        
        # Process may be terminated (exit code 143 for SIGTERM) or fail normally
        # Any non-zero exit is acceptable (terminated or incomplete)
        assert result.ret != 0
        
        # Check for session timeout initialization in output
        output = result.stdout.str() + result.stderr.str()
        # Either we see the session monitor start or the process was terminated
        # Exit codes: 143/137 (positive) or -15/-9 (negative signal numbers)
        assert "Session monitor started" in output or "Session timeout" in output or result.ret in [124, 143, 1, -15, -9]

    def test_session_timeout_env_var(self, pytester, monkeypatch):
        """Test that session timeout can be set via environment variable."""
        monkeypatch.setenv("PYTEST_VIGIL__SESSION_TIMEOUT", "1.0")
        
        pytester.makepyfile("""
            import time
            import pytest

            def test_slow_1():
                time.sleep(0.5)

            def test_slow_2():
                time.sleep(0.5)

            def test_slow_3():
                time.sleep(0.5)
        """)

        result = pytester.runpytest_subprocess("-v")
        
        # Should terminate due to session timeout (non-zero exit)
        assert result.ret != 0
        output = result.stdout.str() + result.stderr.str()
        # Verify session monitor was initialized with the env var value
        assert "Session monitor started" in output or result.ret in [124, 143, 1, -15, -9]

    def test_session_timeout_cli_overrides_env(self, pytester, monkeypatch):
        """Test that CLI option overrides environment variable for session timeout."""
        monkeypatch.setenv("PYTEST_VIGIL__SESSION_TIMEOUT", "10.0")
        
        pytester.makepyfile("""
            import time
            import pytest

            def test_1():
                time.sleep(0.5)

            def test_2():
                time.sleep(0.5)
        """)

        # CLI sets shorter timeout that should trigger
        result = pytester.runpytest_subprocess("--vigil-session-timeout=1", "-v")
        
        # Should terminate or fail
        assert result.ret != 0
        output = result.stdout.str() + result.stderr.str()
        # Verify session monitor started with CLI value
        assert "Session monitor started" in output or result.ret in [124, 143, 1, -15, -9]

    def test_session_timeout_longer_than_suite(self, pytester):
        """Test that session timeout does not interfere when timeout is longer than test suite."""
        pytester.makepyfile("""
            import time
            import pytest

            def test_quick_1():
                time.sleep(0.1)

            def test_quick_2():
                time.sleep(0.1)

            def test_quick_3():
                time.sleep(0.1)
        """)

        # Set very long timeout that won't trigger
        result = pytester.runpytest("--vigil-session-timeout=30", "-v")
        
        # Should pass normally
        result.assert_outcomes(passed=3)

    def test_session_timeout_no_tests(self, pytester):
        """Test session timeout behavior with no tests collected."""
        pytester.makepyfile("""
            # No tests here
            pass
        """)

        result = pytester.runpytest("--vigil-session-timeout=5", "-v")
        
        # Should complete quickly with no tests
        assert result.ret == 5  # pytest.ExitCode.NO_TESTS_COLLECTED
