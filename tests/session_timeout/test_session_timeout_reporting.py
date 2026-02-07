"""
Test session timeout reporting and output.
- Verify exit codes, output messages, and test execution reporting.
"""

pytest_plugins = ["pytester"]


class TestSessionTimeoutReporting:
    """Test session timeout reporting and output."""
    
    def test_session_timeout_exit_code_124(self, pytester):
        """Test that session timeout exits with code 124 (GNU timeout convention)."""
        pytester.makepyfile("""
            import time
            import pytest

            def test_quick():
                time.sleep(0.1)

            def test_hanging():
                time.sleep(10.0)
        """)

        # Set short timeout that will trigger
        result = pytester.runpytest_subprocess("--vigil-session-timeout=1", "-s", "-v")
        
        # Should exit with code 124 (timeout exit code)
        assert result.ret == 124, f"Expected exit code 124, got {result.ret}"
        
        output = result.stdout.str() + result.stderr.str()
        # Verify timeout occurred
        assert "SESSION TIMEOUT EXCEEDED" in output or "Session timeout" in output

    def test_session_timeout_shows_current_test(self, pytester):
        """Test that session timeout message shows which test was executing."""
        pytester.makepyfile("""
            import time
            import pytest

            def test_quick():
                time.sleep(0.1)

            def test_slow_hanging_test():
                '''This test will be running when timeout triggers.'''
                time.sleep(10.0)
        """)

        # Set timeout that will trigger during second test
        result = pytester.runpytest_subprocess("--vigil-session-timeout=1", "-s", "-v")
        
        # Should be terminated
        assert result.ret != 0
        
        output = result.stdout.str() + result.stderr.str()
        
        # Verify the timeout message includes the test name
        assert "Currently executing test:" in output or "test_slow_hanging_test" in output, \
            f"Expected test name in output, but got:\n{output}"
        
        # Verify the banner is displayed
        assert "SESSION TIMEOUT EXCEEDED" in output or "Session timeout exceeded" in output

    def test_session_timeout_clean_exit_no_resource_leaks(self, pytester):
        """Test that session timeout exits cleanly without resource leak warnings."""
        pytester.makepyfile("""
            import time
            import pytest

            def test_quick():
                time.sleep(0.1)

            def test_hanging():
                time.sleep(10.0)
        """)

        result = pytester.runpytest_subprocess("--vigil-session-timeout=1", "-s", "-v")
        
        # Should exit with timeout code
        assert result.ret == 124
        
        output = result.stdout.str() + result.stderr.str()
        
        # Should NOT have resource tracker warnings about leaked semaphores
        # (This was the issue with the old implementation)
        assert "leaked semaphore" not in output.lower(), \
            f"Found resource leak warning in output:\n{output}"

    def test_session_timeout_between_tests_shows_last_test(self, pytester):
        """Test that session timeout shows last executed test when timeout occurs between tests."""
        pytester.makepyfile("""
            import time
            import pytest

            def test_quick_first():
                '''First test completes quickly.'''
                time.sleep(0.1)

            def test_with_delay_before():
                '''This test has a slow fixture setup that triggers timeout.'''
                time.sleep(10.0)  # Timeout will occur during this sleep
        """)

        # Set timeout that will trigger after first test completes but during fixture/setup
        result = pytester.runpytest_subprocess("--vigil-session-timeout=0.5", "-s", "-v")
        
        # Should be terminated
        assert result.ret != 0
        
        output = result.stdout.str() + result.stderr.str()
        
        # Verify the timeout message includes the last test name
        # Either we caught it during execution or between tests
        assert ("Last executed test:" in output or "test_quick_first" in output), \
            f"Expected last test name in output, but got:\n{output}"
        
        # Verify the banner is displayed
        assert "SESSION TIMEOUT EXCEEDED" in output or "Session timeout exceeded" in output
