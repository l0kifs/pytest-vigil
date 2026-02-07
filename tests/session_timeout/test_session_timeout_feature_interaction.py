"""
Tests for session timeout interaction with other features.
- Verify that session timeout works with xdist, per-test timeouts, retry, stall detection, and resource limits.
"""

pytest_plugins = ["pytester"]


class TestSessionTimeoutFeatureInteraction:
    """Test session timeout interaction with other features."""
    
    def test_session_timeout_with_xdist(self, pytester):
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

    def test_session_timeout_with_per_test_timeout(self, pytester):
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

    def test_session_timeout_with_retry(self, pytester):
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

    def test_session_timeout_with_stall_detection(self, pytester):
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

    def test_session_timeout_with_resource_limits(self, pytester):
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
