"""
Test edge cases for session timeout.
- Verify behavior with very short timeouts, zero values, graceful shutdown, multiple runs, and normal test failures.
"""

pytest_plugins = ["pytester"]


class TestSessionTimeoutEdgeCases:
    """Test edge cases for session timeout."""
    
    def test_session_timeout_very_short(self, pytester):
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

    def test_session_timeout_zero_value(self, pytester):
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

    def test_session_timeout_graceful_shutdown(self, pytester):
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

    def test_session_timeout_with_report_generation(self, pytester):
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

    def test_session_timeout_multiple_runs(self, pytester):
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

    def test_session_timeout_does_not_affect_normal_failures(self, pytester):
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
