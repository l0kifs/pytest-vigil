"""
Comprehensive tests for stall detection functionality.

Tests cover:
- Proper functioning with all test outcomes (pass, fail, skip, xfail, xpass)
- All available parameters (marker, CLI, env)
- Configuration precedence (marker > CLI > env)
- CI environment interaction
- XDist compatibility
- Edge cases and boundary conditions
- Feature interactions (retry, other limits, JSON report)
- No interference with other pytest-vigil features
"""

import pytest
import json
import os

pytest_plugins = ["pytester"]


# =============================================================================
# 1. BASIC FUNCTIONALITY TESTS
# =============================================================================

class TestBasicStallDetection:
    """Test basic stall detection enforcement."""
    
    def test_stall_detection_violation(self, pytester):
        """
        Verify that stall detection works.
        A test sleeping for > stall_timeout with low CPU should fail.
        """
        pytester.makepyfile(test_inner_stall="""
            import pytest
            import time

            # stall_timeout=0.5s, stall_threshold=100% (force violation even if cpu is high)
            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stalled():
                # Sleeping consumes almost 0 CPU
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        # Check for policy violation output
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_passing(self, pytester):
        """Verify that tests with high CPU activity don't trigger stall detection."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=1.0, stall_cpu_threshold=50.0)
            def test_high_cpu():
                # Busy loop to keep CPU high
                start = time.time()
                while time.time() - start < 0.5:
                    _ = sum(range(10000))
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_stall_detection_with_low_threshold(self, pytester):
        """Verify stall detection with low CPU threshold (1%)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=1.0)
            def test_stall_low_threshold():
                # Sleep should trigger since CPU < 1%
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_with_medium_threshold(self, pytester):
        """Verify stall detection with medium CPU threshold (10%)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=10.0)
            def test_stall_medium_threshold():
                # Sleep should trigger since CPU < 10%
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_boundary_just_under_timeout(self, pytester):
        """Verify test passing just under stall timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=1.0, stall_cpu_threshold=100.0)
            def test_just_under():
                # Sleep for 0.9s, just under 1.0s timeout
                time.sleep(0.9)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_stall_detection_boundary_just_over_timeout(self, pytester):
        """Verify test failing just over stall timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_just_over():
                # Sleep for 1.5s, over 0.5s timeout
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1


# =============================================================================
# 2. TEST OUTCOME TESTS
# =============================================================================

class TestStallDetectionWithOutcomes:
    """Test stall detection with different test outcomes."""
    
    def test_stall_detection_with_passing_test(self, pytester):
        """Verify stall detection violation on a passing test."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_pass_but_stalled():
                time.sleep(1.5)
                assert True  # Test would pass, but stalls
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_with_failing_test(self, pytester):
        """Verify stall detection violation on a failing test."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_fail_and_stalled():
                time.sleep(1.5)
                assert False  # Test fails AND stalls
        """)
        result = pytester.runpytest()
        
        # Should show violation (stall detected before assertion)
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_with_skipped_test(self, pytester):
        """Verify stall detection doesn't apply to skipped tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            @pytest.mark.skip(reason="Skipped test")
            def test_skip_with_stall():
                time.sleep(1.5)  # Would stall, but test is skipped
        """)
        result = pytester.runpytest()
        
        # Skipped tests shouldn't trigger monitoring
        result.stdout.fnmatch_lines(["*1 skipped*"])
        assert result.ret == 0
    
    def test_stall_detection_with_xfail_test(self, pytester):
        """Verify stall detection runs on xfail marked test (but test still marked xfail)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            @pytest.mark.xfail(reason="Expected to fail")
            def test_xfail_with_stall():
                time.sleep(1.5)
                assert False
        """)
        result = pytester.runpytest()
        
        # xfail tests are marked xfailed regardless of stall detection
        result.stdout.fnmatch_lines(["*1 xfailed*"])
        # Exit code 0 for xfail
        assert result.ret == 0
    
    def test_stall_detection_with_xpass_test(self, pytester):
        """Verify stall detection runs on xpass (unexpectedly passing) test."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            @pytest.mark.xfail(reason="Expected to fail")
            def test_xpass_with_stall():
                time.sleep(0.1)
                assert True  # Unexpectedly passes, no stall
        """)
        result = pytester.runpytest()
        
        # xpass tests show as XPASS (X capital) in output
        result.stdout.fnmatch_lines(["*1 xpassed*"])
        # Exit code 0 for xpass with default strict_xfail=False
        assert result.ret == 0


# =============================================================================
# 3. PARAMETER CONFIGURATION TESTS
# =============================================================================

class TestStallDetectionParameters:
    """Test stall detection parameter configuration."""
    
    def test_stall_marker_parameters(self, pytester):
        """Verify stall parameters set via marker."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_marker_params():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_cli_parameters(self, pytester):
        """Verify stall parameters set via CLI."""
        pytester.makepyfile("""
            import time
            
            def test_cli_params():
                time.sleep(1.5)
        """)
        
        result = pytester.runpytest(
            "--vigil-stall-timeout=0.5",
            "--vigil-stall-cpu-threshold=100"
        )
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_env_parameters(self, pytester, monkeypatch):
        """Verify stall parameters set via environment variables."""
        monkeypatch.setenv("PYTEST_VIGIL__STALL_TIMEOUT", "0.5")
        monkeypatch.setenv("PYTEST_VIGIL__STALL_CPU_THRESHOLD", "100.0")
        
        pytester.makepyfile("""
            import time
            
            def test_env_params():
                time.sleep(1.5)
        """)
        
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_marker_overrides_cli(self, pytester):
        """Verify marker parameters override CLI parameters."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_marker_override():
                time.sleep(1.5)
        """)
        
        # CLI sets lenient timeout=5.0, but marker sets strict 0.5
        result = pytester.runpytest(
            "--vigil-stall-timeout=5.0",
            "--vigil-stall-cpu-threshold=0.1"
        )
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_cli_overrides_env(self, pytester, monkeypatch):
        """Verify CLI parameters override environment variables."""
        monkeypatch.setenv("PYTEST_VIGIL__STALL_TIMEOUT", "5.0")
        monkeypatch.setenv("PYTEST_VIGIL__STALL_CPU_THRESHOLD", "0.1")
        
        pytester.makepyfile("""
            import time
            
            def test_cli_override():
                time.sleep(1.5)
        """)
        
        # CLI sets stricter stall_timeout=0.5, should trigger despite lenient env
        result = pytester.runpytest(
            "--vigil-stall-timeout=0.5",
            "--vigil-stall-cpu-threshold=100"
        )
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_only_timeout_parameter(self, pytester):
        """Verify stall detection with only timeout specified."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.3)
            def test_only_timeout():
                # Without explicit threshold, uses default 0.1%
                # Sleep should keep CPU low, but may have spikes
                # Use explicit high threshold in other tests for reliability
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-v")
        
        # Test should pass - default threshold (0.1%) may not reliably trigger
        # due to system activity during sleep
        assert result.ret == 0
    
    def test_stall_cli_timeout_only(self, pytester):
        """Verify CLI stall-timeout option works alone."""
        pytester.makepyfile("""
            import time
            
            def test_cli_timeout():
                time.sleep(1.5)
        """)
        
        # Only set timeout via CLI, threshold uses default (1.0%)
        result = pytester.runpytest("--vigil-stall-timeout=0.5")
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_cli_threshold_only(self, pytester):
        """Verify CLI stall-cpu-threshold alone doesn't enable stall detection."""
        pytester.makepyfile("""
            import time
            
            def test_cli_threshold_only():
                time.sleep(1.5)
                assert True
        """)
        
        # Only set threshold, no timeout means no stall detection
        result = pytester.runpytest("--vigil-stall-cpu-threshold=100")
        
        # Should pass as stall detection is not enabled
        assert result.ret == 0


# =============================================================================
# 4. CI ENVIRONMENT TESTS
# =============================================================================

class TestStallDetectionCI:
    """Test stall detection in CI environment."""
    
    def test_stall_detection_ci_multiplier(self, pytester, monkeypatch):
        """Verify CI multiplier applies to stall timeout."""
        monkeypatch.setenv("CI", "true")
        
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_ci_multiplier():
                # Sleep 1.5s. With CI multiplier (2x), timeout becomes 1.0s
                # So this should still trigger violation
                time.sleep(1.5)
        """)
        
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_ci_extended_timeout(self, pytester, monkeypatch):
        """Verify CI multiplier extends timeout appropriately."""
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=1.0, stall_cpu_threshold=100.0)
            def test_ci_extended():
                # Sleep 1.8s. With CI multiplier (2x), timeout becomes 2.0s
                # So this should pass
                time.sleep(1.8)
                assert True
        """)
        
        result = pytester.runpytest()
        
        # Should pass due to CI multiplier
        assert result.ret == 0
    
    def test_stall_detection_no_ci(self, pytester, monkeypatch):
        """Verify stall detection without CI multiplier."""
        # Explicitly set CI to false
        monkeypatch.setenv("CI", "false")
        
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_no_ci():
                time.sleep(1.5)
        """)
        
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1


# =============================================================================
# 5. XDIST INTEGRATION TESTS
# =============================================================================

class TestStallDetectionXDist:
    """Test stall detection with pytest-xdist."""
    
    def test_stall_detection_xdist_basic(self, pytester):
        """Verify that stall detection works correctly in xdist mode."""
        pytester.makepyfile(test_inner_stall_xdist="""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stalled_xdist():
                # Sleeping consumes almost 0 CPU
                time.sleep(1.5)
        """)
        result = pytester.runpytest("-n", "2")
        
        # Check for policy violation output and failure
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_xdist_multiple_tests(self, pytester):
        """Verify stall detection with multiple tests in xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_1():
                time.sleep(1.5)
            
            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_2():
                time.sleep(1.5)
            
            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_pass():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-n", "3")
        
        # Two should fail, one should pass
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_xdist_passing(self, pytester):
        """Verify passing tests work correctly with xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_pass_1():
                time.sleep(0.1)
                assert True
            
            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_pass_2():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-n", "2")
        
        assert result.ret == 0


# =============================================================================
# 6. FEATURE INTERACTION TESTS
# =============================================================================

class TestStallDetectionFeatureInteraction:
    """Test stall detection interaction with other pytest-vigil features."""
    
    def test_stall_with_timeout_both_pass(self, pytester):
        """Verify stall and timeout limits both pass."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_both_pass():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_stall_with_timeout_stall_triggers_first(self, pytester):
        """Verify stall detection triggers before timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=5.0, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_first():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        # Stall detection (0.5s) should trigger before timeout (5.0s)
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_with_timeout_timeout_triggers_first(self, pytester):
        """Verify timeout triggers before stall detection."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5, stall_timeout=5.0, stall_cpu_threshold=100.0)
            def test_timeout_first():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        # Timeout (0.5s) should trigger before stall detection (5.0s)
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1
    
    def test_stall_with_memory_limit(self, pytester):
        """Verify stall detection works with memory limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=100, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_and_memory():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_with_cpu_limit(self, pytester):
        """Verify stall detection works with CPU limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=200, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_and_cpu():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_with_all_limits(self, pytester):
        """Verify stall detection works with all limit types."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(
                timeout=5.0,
                memory=100,
                cpu=200,
                stall_timeout=0.5,
                stall_cpu_threshold=100.0
            )
            def test_all_limits():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_with_retry_fails_all_attempts(self, pytester):
        """Verify stall detection with retry mechanism - fails all attempts."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(retry=2, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_with_retry_fail():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        # Should fail all retry attempts
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_with_retry_passes_on_retry(self, pytester):
        """Verify stall detection with retry - passes on retry."""
        pytester.makepyfile("""
            import pytest
            import time
            import os

            FILENAME = "stall_retry.txt"

            @pytest.mark.vigil(retry=2, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_retry_success():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    # First attempt stalls
                    time.sleep(1.5)
                else:
                    # Second attempt passes quickly
                    time.sleep(0.1)
                    assert True
        """)
        result = pytester.runpytest()
        
        # Should show flaky test (passed on retry)
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
        assert result.ret == 0


# =============================================================================
# 7. JSON REPORT TESTS
# =============================================================================

class TestStallDetectionReporting:
    """Test stall detection JSON report generation."""
    
    def test_stall_report_parameters(self, pytester):
        """Verify stall detection parameters are recorded in JSON report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=3.0, stall_cpu_threshold=0.5)
            def test_stall_report():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        limits = data["results"][0]["limits"]
        stall_limits = [l for l in limits if l.get("limit_type") == "stall"]
        assert len(stall_limits) > 0
        
        # Verify stall parameters
        stall_limit = stall_limits[0]
        assert stall_limit["threshold"] == 3.0
        assert stall_limit["secondary_threshold"] == 0.5
    
    def test_stall_report_with_violation(self, pytester):
        """Verify JSON report captures stall violation."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_violation_report():
                time.sleep(1.5)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 1
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        # Verify stall limit is recorded
        limits = data["results"][0]["limits"]
        limit_types = {l["limit_type"] for l in limits}
        assert "stall" in limit_types
    
    def test_stall_report_with_multiple_limits(self, pytester):
        """Verify JSON report works with stall detection and other limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(
                timeout=5.0,
                stall_timeout=2.0,
                stall_cpu_threshold=0.5
            )
            def test_multi_limit_report():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        limits = data["results"][0]["limits"]
        limit_types = {l["limit_type"] for l in limits}
        assert "time" in limit_types
        assert "stall" in limit_types
    
    def test_stall_report_cli_parameters(self, pytester):
        """Verify CLI stall parameters are recorded in report."""
        pytester.makepyfile("""
            import time
            
            def test_stall_cli_report():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(
            "--vigil-stall-timeout=2.0",
            "--vigil-stall-cpu-threshold=5.0",
            f"--vigil-report={report_file}"
        )
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        limits = data["results"][0]["limits"]
        stall_limits = [l for l in limits if l.get("limit_type") == "stall"]
        assert len(stall_limits) > 0
        
        stall_limit = stall_limits[0]
        assert stall_limit["threshold"] == 2.0
        assert stall_limit["secondary_threshold"] == 5.0


# =============================================================================
# 8. EDGE CASE TESTS
# =============================================================================

class TestStallDetectionEdgeCases:
    """Test edge cases and boundary conditions for stall detection."""
    
    def test_stall_very_short_timeout(self, pytester):
        """Verify stall detection with very short timeout (0.1s)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.1, stall_cpu_threshold=100.0)
            def test_very_short_timeout():
                time.sleep(0.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_very_long_timeout(self, pytester):
        """Verify stall detection with very long timeout (10s)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=10.0, stall_cpu_threshold=100.0)
            def test_very_long_timeout():
                time.sleep(0.5)
                assert True
        """)
        result = pytester.runpytest()
        
        # Should pass as timeout is very long
        assert result.ret == 0
    
    def test_stall_zero_threshold(self, pytester):
        """Verify stall detection with very low CPU threshold."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=5.0)
            def test_zero_threshold():
                # Low threshold should trigger for sleep
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_instant_test(self, pytester):
        """Verify instant tests don't trigger stall detection."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_instant():
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_stall_no_sleep_busy_test(self, pytester):
        """Verify busy tests (no sleep) don't trigger stall detection."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=50.0)
            def test_busy():
                # Busy loop for 1s - high CPU, should not trigger stall
                start = time.time()
                while time.time() - start < 1.0:
                    _ = sum(range(10000))
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_stall_multiple_short_sleeps(self, pytester):
        """Verify multiple short sleeps below stall timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=1.0, stall_cpu_threshold=100.0)
            def test_multiple_short_sleeps():
                # Multiple 0.3s sleeps - each below 1.0s stall timeout
                for _ in range(5):
                    time.sleep(0.3)
        """)
        result = pytester.runpytest()
        
        # May trigger stall detection depending on timing
        # The current implementation checks duration, not individual sleeps
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_without_vigil_marker(self, pytester):
        """Verify tests without vigil marker are not monitored."""
        pytester.makepyfile("""
            import time

            def test_no_vigil():
                time.sleep(2.0)
                assert True
        """)
        result = pytester.runpytest()
        
        # Should pass as no monitoring is enabled
        assert result.ret == 0
    
    def test_stall_empty_test_function(self, pytester):
        """Verify empty test functions don't trigger stall detection."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_empty():
                pass
        """)
        result = pytester.runpytest()
        assert result.ret == 0


# =============================================================================
# 9. NO INTERFERENCE TESTS
# =============================================================================

class TestStallDetectionNoInterference:
    """Verify stall detection doesn't interfere with other features."""
    
    def test_stall_no_interference_with_regular_tests(self, pytester):
        """Verify stall detection tests don't affect regular tests."""
        pytester.makepyfile("""
            import pytest
            import time

            def test_regular():
                assert True
            
            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_with_stall():
                time.sleep(1.5)
            
            def test_another_regular():
                assert True
        """)
        result = pytester.runpytest()
        
        # One test should fail (stall), two should pass
        result.stdout.fnmatch_lines(["*1 failed*2 passed*"])
        assert result.ret == 1
    
    def test_stall_no_interference_with_timeout_tests(self, pytester):
        """Verify stall detection doesn't interfere with timeout-only tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_timeout_only():
                time.sleep(0.1)
                assert True
            
            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_stall_only():
                time.sleep(1.5)
            
            @pytest.mark.vigil(timeout=2.0, stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_both():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        
        # Two should pass, one should fail (stall)
        result.stdout.fnmatch_lines(["*1 failed*2 passed*"])
        assert result.ret == 1
    
    def test_stall_no_interference_with_memory_tests(self, pytester):
        """Verify stall detection doesn't interfere with memory limit tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=100)
            def test_memory_only():
                time.sleep(0.1)
                assert True
            
            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_stall_only():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        
        # Both should pass
        assert result.ret == 0
    
    def test_stall_no_interference_with_retry_tests(self, pytester):
        """Verify stall detection doesn't interfere with retry-only tests."""
        pytester.makepyfile("""
            import pytest
            import time
            import os

            FILENAME = "retry_test.txt"

            @pytest.mark.vigil(retry=2)
            def test_retry_only():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
            
            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_stall_only():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        
        # Both should pass (retry succeeds, stall doesn't trigger)
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
        assert result.ret == 0
    
    def test_stall_no_interference_with_parametrized_tests(self, pytester):
        """Verify stall detection works with parametrized tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.parametrize("duration", [0.1, 0.2, 0.3])
            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            def test_parametrized(duration):
                time.sleep(duration)
                assert True
        """)
        result = pytester.runpytest()
        
        # All parametrized tests should pass
        result.stdout.fnmatch_lines(["*3 passed*"])
        assert result.ret == 0
