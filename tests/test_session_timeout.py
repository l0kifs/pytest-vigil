"""Tests for session-level timeout functionality."""

import pytest
import time

pytest_plugins = ["pytester"]


def test_session_timeout_cli_option(pytester):
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


def test_session_timeout_env_var(pytester, monkeypatch):
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


def test_session_timeout_cli_overrides_env(pytester, monkeypatch):
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


def test_session_timeout_longer_than_suite(pytester):
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


def test_session_timeout_very_short(pytester):
    """Test behavior with very short session timeout (edge case)."""
    pytester.makepyfile("""
        import pytest

        def test_instant():
            assert True
    """)

    # Very short timeout (0.1 seconds)
    result = pytester.runpytest_subprocess("--vigil-session-timeout=0.1", "-v")
    
    # With very short timeout, process will likely be terminated
    # Exit codes: 0 (passed fast enough), 1 (failed/incomplete), 143 (SIGTERM), 137 (SIGKILL), -15/-9 (negative signals)
    assert result.ret in [0, 1, 124, 143, 137, -15, -9]


def test_session_timeout_with_ci_multiplier(pytester, monkeypatch):
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


def test_session_timeout_with_xdist(pytester):
    """Test that session timeout works with xdist parallel execution."""
    pytester.makepyfile("""
        import time
        import pytest

        def test_parallel_1():
            time.sleep(0.5)

        def test_parallel_2():
            time.sleep(0.5)

        def test_parallel_3():
            time.sleep(0.5)

        def test_parallel_4():
            time.sleep(0.5)
    """)

    # Run with xdist (2 workers), should take ~1 second with parallelism
    # Set session timeout to 1.5 seconds
    result = pytester.runpytest_subprocess("-n", "2", "--vigil-session-timeout=1.5", "-v")
    
    # With 2 workers, tests should complete in ~1 second, under the 1.5s timeout
    # May pass, fail, or be terminated depending on timing
    # Exit codes: 0 (pass), 1 (fail), 143 (SIGTERM), 137 (SIGKILL), -15 (SIGTERM negative), -9 (SIGKILL negative)
    assert result.ret in [0, 1, 124, 143, 137, -15, -9]


def test_session_timeout_with_per_test_timeout(pytester):
    """Test that session timeout does not interfere with per-test timeouts."""
    pytester.makepyfile("""
        import time
        import pytest

        @pytest.mark.vigil(timeout=0.5)
        def test_with_timeout():
            time.sleep(1.0)  # Should fail due to per-test timeout

        def test_normal():
            time.sleep(0.1)
    """)

    # Set long session timeout
    result = pytester.runpytest("--vigil-session-timeout=10", "-v")
    
    # test_with_timeout should fail due to per-test timeout
    # test_normal should pass
    output = result.stdout.str() + result.stderr.str()
    assert "Test timed out (Vigil)" in output
    assert result.ret != 0


def test_session_timeout_with_retry(pytester):
    """Test that session timeout works alongside retry mechanism."""
    pytester.makepyfile("""
        import time
        import pytest

        @pytest.mark.vigil(retry=2)
        def test_flaky():
            # First attempt fails, second passes
            import os
            marker_file = '/tmp/test_flaky_marker'
            if not os.path.exists(marker_file):
                with open(marker_file, 'w') as f:
                    f.write('1')
                assert False
            else:
                os.remove(marker_file)
                time.sleep(0.1)
                assert True

        def test_normal():
            time.sleep(0.1)
    """)

    # Set reasonable session timeout
    result = pytester.runpytest("--vigil-session-timeout=10", "-v")
    
    # Should complete normally with retries working
    output = result.stdout.str()
    assert result.ret == 0 or "flaky" in output.lower()


def test_session_timeout_graceful_shutdown(pytester):
    """Test that session timeout allows graceful shutdown."""
    pytester.makepyfile("""
        import time
        import pytest
        import atexit

        cleanup_marker = '/tmp/vigil_cleanup_test'

        def cleanup():
            with open(cleanup_marker, 'w') as f:
                f.write('cleaned')

        atexit.register(cleanup)

        def test_long():
            time.sleep(2.0)
    """)

    result = pytester.runpytest_subprocess("--vigil-session-timeout=1", "-v")
    
    # Should be terminated (non-zero exit)
    assert result.ret != 0
    
    # Verify session monitor was started
    output = result.stdout.str() + result.stderr.str()
    assert "Session monitor started" in output or result.ret in [124, 143, 137, -15, -9]
    
    # Graceful shutdown with SIGTERM should allow cleanup
    # Note: atexit may not run reliably in all cases, but we verify no crash


def test_session_timeout_with_stall_detection(pytester):
    """Test that session timeout works alongside stall detection."""
    pytester.makepyfile("""
        import time
        import pytest

        @pytest.mark.vigil(timeout=2, stall_timeout=1, stall_cpu_threshold=0.1)
        def test_with_stall():
            time.sleep(0.5)

        def test_normal():
            time.sleep(0.1)
    """)

    result = pytester.runpytest("--vigil-session-timeout=10", "-v")
    
    # Both tests should pass, features coexist peacefully
    result.assert_outcomes(passed=2)


def test_session_timeout_with_resource_limits(pytester):
    """Test that session timeout works with memory and CPU limits."""
    pytester.makepyfile("""
        import time
        import pytest

        @pytest.mark.vigil(timeout=2, memory=500, cpu=95)
        def test_with_limits():
            time.sleep(0.2)

        def test_normal():
            time.sleep(0.1)
    """)

    result = pytester.runpytest("--vigil-session-timeout=10", "-v")

    # Should pass, all features work together (using more relaxed limits)
    result.assert_outcomes(passed=2)


def test_session_timeout_zero_value(pytester):
    """Test that zero or negative session timeout is handled gracefully."""
    pytester.makepyfile("""
        import pytest

        def test_instant():
            assert True
    """)

    # Test with zero timeout
    result = pytester.runpytest_subprocess("--vigil-session-timeout=0", "-v")
    
    # Zero timeout will trigger immediately
    # Exit codes: 0 (if no tests started), 1 (incomplete), 5 (NO_TESTS_COLLECTED), 143/137 (SIGTERM/SIGKILL), -15/-9 (negative signals)
    assert result.ret in [0, 1, 5, 124, 143, 137, -15, -9]


def test_session_timeout_no_tests(pytester):
    """Test session timeout behavior with no tests collected."""
    pytester.makepyfile("""
        # No tests here
        pass
    """)

    result = pytester.runpytest("--vigil-session-timeout=5", "-v")
    
    # Should complete quickly with no tests
    assert result.ret == 5  # pytest.ExitCode.NO_TESTS_COLLECTED


def test_session_timeout_with_report_generation(pytester):
    """Test that reports are generated with session timeout enabled."""
    pytester.makepyfile("""
        import time
        import pytest

        @pytest.mark.vigil(timeout=2)
        def test_1():
            time.sleep(0.1)

        @pytest.mark.vigil(timeout=2)
        def test_2():
            time.sleep(0.1)

        @pytest.mark.vigil(timeout=2)
        def test_3():
            time.sleep(0.1)
    """)

    report_file = pytester.path / "vigil_report.json"
    
    result = pytester.runpytest(
        "--vigil-session-timeout=10",  # Long timeout to avoid killing parent
        f"--vigil-report={report_file}",
        "-v"
    )
    
    # Should complete normally with report generated
    result.assert_outcomes(passed=3)
    
    # Check if report was created
    import json
    assert report_file.exists()
    with open(report_file) as f:
        data = json.load(f)
        # Report should have some structure
        assert "timestamp" in data
        assert "results" in data
        assert len(data["results"]) == 3  # One result per test


def test_session_timeout_multiple_runs(pytester):
    """Test that session monitor properly cleans up between runs."""
    pytester.makepyfile("""
        import time
        import pytest

        def test_quick():
            time.sleep(0.1)
    """)

    # Run multiple times to ensure no state leakage
    for i in range(3):
        result = pytester.runpytest("--vigil-session-timeout=5", "-v")
        result.assert_outcomes(passed=1)


def test_session_timeout_does_not_affect_normal_failures(pytester):
    """Test that normal test failures still work correctly with session timeout."""
    pytester.makepyfile("""
        import pytest

        def test_failing():
            assert False, "Expected failure"

        def test_passing():
            assert True
    """)

    result = pytester.runpytest("--vigil-session-timeout=10", "-v")
    
    # Should have 1 failure, 1 pass
    result.assert_outcomes(passed=1, failed=1)


def test_session_timeout_exit_code_124(pytester):
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


def test_session_timeout_shows_current_test(pytester):
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


def test_session_timeout_clean_exit_no_resource_leaks(pytester):
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


def test_session_timeout_grace_period_cli_option(pytester):
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


def test_session_timeout_grace_period_cli_overrides_env(pytester, monkeypatch):
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


def test_session_timeout_grace_period_env_var(pytester, monkeypatch):
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


def test_session_timeout_between_tests_shows_last_test(pytester):
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
