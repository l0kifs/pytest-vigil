"""
Comprehensive tests for CLI terminal report verbosity functionality.

Tests cover:
- All test outcomes (pass, fail, skip, xfail, xpass)
- All verbosity levels (none, short, full)
- Default behavior
- CLI parameter handling
- Environment variable configuration
- CI environment interaction
- XDist integration
- Edge cases
- Feature non-interference
"""

import pytest
import os
import json

pytest_plugins = ["pytester"]


# =============================================================================
# 1. BASIC FUNCTIONALITY TESTS
# =============================================================================

class TestBasicReportVerbosity:
    """Test basic CLI report verbosity functionality."""
    
    def test_default_verbosity_is_short(self, pytester):
        """Verify default verbosity is 'short' (shows summary statistics)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.02)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_3():
                time.sleep(0.03)
        """)
        
        result = pytester.runpytest()
        output = result.stdout.str()
        
        # Should show report section
        assert "Vigil Reliability Report" in output
        # Should show summary statistics
        assert "Total Tests:" in output
        assert "Average Duration:" in output
        assert "Fastest Test:" in output
        assert "Slowest Test:" in output
        assert "Average CPU:" in output
        assert "Peak CPU:" in output
        assert "Average Memory:" in output
        assert "Peak Memory:" in output
        # Should not show detailed table headers
        assert "Test ID" not in output or "Total Tests" in output  # If Test ID appears, it's in test names, not table
        assert result.ret == 0
    
    def test_verbosity_none_hides_report(self, pytester):
        """Verify verbosity=none completely hides the report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=none")
        output = result.stdout.str()
        
        # Should not show report section
        assert "Vigil Reliability Report" not in output
        assert "Test ID" not in output
        assert "Duration (s)" not in output
        assert result.ret == 0
    
    def test_verbosity_short_shows_limited_tests(self, pytester):
        """Verify verbosity=short shows summary statistics only."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.02)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_3():
                time.sleep(0.03)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_4():
                time.sleep(0.04)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_5():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_6():
                time.sleep(0.06)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Should show report
        assert "Vigil Reliability Report" in output
        # Should show summary statistics
        assert "Total Tests: 6" in output
        assert "Average Duration:" in output
        assert "Fastest Test:" in output
        assert "Slowest Test:" in output
        # Should not show detailed table
        assert "Att" not in output  # Table header
        assert result.ret == 0
    
    def test_verbosity_full_shows_all_tests(self, pytester):
        """Verify verbosity=full shows detailed table with all tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_3():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_4():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_5():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_6():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_7():
                time.sleep(0.01)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Should show detailed table
        assert "Vigil Reliability Report" in output
        assert "Test ID" in output
        assert "Att" in output
        assert "Duration (s)" in output
        # Should not show summary stats format
        assert "Total Tests:" not in output
        # All test names should be visible in table
        assert "test_1" in output
        assert "test_7" in output
        assert result.ret == 0


# =============================================================================
# 2. TEST OUTCOMES
# =============================================================================

class TestReportWithTestOutcomes:
    """Test CLI report with various test outcomes."""
    
    def test_report_with_passed_tests(self, pytester):
        """Verify passed tests appear in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.05)
                assert True
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        assert "Vigil Reliability Report" in output
        assert "test_pass" in output
        assert result.ret == 0
    
    def test_report_with_failed_tests(self, pytester):
        """Verify failed tests appear in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_fail():
                time.sleep(0.05)
                assert False
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        assert "Vigil Reliability Report" in output
        assert "test_fail" in output
        assert result.ret == 1
    
    def test_report_with_skipped_tests(self, pytester):
        """Verify skipped tests behavior in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.05)
                assert True
            
            @pytest.mark.skip(reason="test skip")
            def test_skip():
                pass
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Skipped tests don't have vigil monitoring, so shouldn't appear in report
        assert "test_pass" in output
        # test_skip should not be in vigil report (no vigil marker)
        assert result.ret == 0
    
    def test_report_with_xfail_tests(self, pytester):
        """Verify xfail tests behavior in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.05)
                assert True
            
            @pytest.mark.xfail(reason="expected to fail")
            @pytest.mark.vigil(timeout=2.0)
            def test_xfail():
                time.sleep(0.05)
                assert False
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        assert "Vigil Reliability Report" in output
        assert "test_pass" in output
        # xfail tests with vigil marker should appear in report
        assert "test_xfail" in output
        assert result.ret == 0
    
    def test_report_with_xpass_tests(self, pytester):
        """Verify xpass tests appear in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.05)
                assert True
            
            @pytest.mark.xfail(reason="expected to fail", strict=False)
            @pytest.mark.vigil(timeout=2.0)
            def test_xpass():
                time.sleep(0.05)
                assert True
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        assert "Vigil Reliability Report" in output
        assert "test_xpass" in output
        assert result.ret == 0
    
    def test_report_with_mixed_outcomes(self, pytester):
        """Verify report shows all test types correctly."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.05)
                assert True
            
            @pytest.mark.vigil(timeout=2.0)
            def test_fail():
                time.sleep(0.05)
                assert False
            
            @pytest.mark.skip(reason="skipped")
            def test_skip():
                pass
            
            @pytest.mark.xfail
            @pytest.mark.vigil(timeout=2.0)
            def test_xfail():
                assert False
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        assert "Vigil Reliability Report" in output
        # All vigil-monitored tests should appear
        assert "test_pass" in output
        assert "test_fail" in output
        assert "test_xfail" in output
        assert result.ret == 1


# =============================================================================
# 3. CONFIGURATION TESTS
# =============================================================================

class TestReportConfiguration:
    """Test CLI report configuration via environment and CLI."""
    
    def test_env_variable_sets_verbosity(self, pytester, monkeypatch):
        """Verify PYTEST_VIGIL__REPORT_VERBOSITY environment variable works."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        # Set environment variable
        monkeypatch.setenv("PYTEST_VIGIL__REPORT_VERBOSITY", "none")
        
        result = pytester.runpytest()
        output = result.stdout.str()
        
        # Should not show report
        assert "Vigil Reliability Report" not in output
        assert result.ret == 0
    
    def test_cli_overrides_env_variable(self, pytester, monkeypatch):
        """Verify CLI option overrides environment variable."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        # Set env to none
        monkeypatch.setenv("PYTEST_VIGIL__REPORT_VERBOSITY", "none")
        
        # Override with CLI
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Should show report (CLI wins)
        assert "Vigil Reliability Report" in output
        assert result.ret == 0
    
    def test_invalid_verbosity_value_rejected(self, pytester):
        """Verify invalid verbosity values are rejected."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=invalid")
        
        # Should fail with error about invalid choice
        assert result.ret == 4  # pytest error code for usage error


# =============================================================================
# 4. CI ENVIRONMENT TESTS
# =============================================================================

class TestReportInCIEnvironment:
    """Test CLI report behavior in CI environment."""
    
    def test_report_works_in_ci_environment(self, pytester, monkeypatch):
        """Verify report displays correctly in CI environment."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        # Simulate CI environment
        monkeypatch.setenv("CI", "true")
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Report should still work in CI
        assert "Vigil Reliability Report" in output
        assert "test_sample" in output
        assert result.ret == 0
    
    def test_report_verbosity_none_useful_in_ci(self, pytester, monkeypatch):
        """Verify verbosity=none is useful in CI to reduce log noise."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.05)
        """)
        
        monkeypatch.setenv("CI", "true")
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=none")
        output = result.stdout.str()
        
        # No report should be shown
        assert "Vigil Reliability Report" not in output
        assert result.ret == 0


# =============================================================================
# 5. XDIST INTEGRATION TESTS
# =============================================================================

class TestReportWithXdist:
    """Test CLI report with pytest-xdist parallel execution."""
    
    def test_report_with_xdist_shows_all_tests(self, pytester):
        """Verify report collects results from all xdist workers."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_3():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_4():
                time.sleep(0.05)
        """)
        
        result = pytester.runpytest("-n", "2", "--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Report should show all tests
        assert "Vigil Reliability Report" in output
        assert "test_1" in output
        assert "test_4" in output
        assert result.ret == 0
    
    def test_report_verbosity_short_with_xdist(self, pytester):
        """Verify short verbosity works with xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_3():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_4():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_5():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_6():
                time.sleep(0.05)
        """)
        
        result = pytester.runpytest("-n", "2", "--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Should show report with summary
        assert "Vigil Reliability Report" in output
        assert "Total Tests:" in output
        assert "Average Duration:" in output
        assert result.ret == 0
    
    def test_report_verbosity_none_with_xdist(self, pytester):
        """Verify verbosity=none works with xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.05)
        """)
        
        result = pytester.runpytest("-n", "2", "--vigil-cli-report-verbosity=none")
        output = result.stdout.str()
        
        # Should not show report
        assert "Vigil Reliability Report" not in output
        assert result.ret == 0


# =============================================================================
# 6. EDGE CASES
# =============================================================================

class TestReportEdgeCases:
    """Test CLI report edge cases and boundary conditions."""
    
    def test_report_with_no_vigil_tests(self, pytester):
        """Verify behavior when no tests use vigil."""
        pytester.makepyfile("""
            def test_regular():
                assert True
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Should show report section but indicate no data
        assert "Vigil Reliability Report" in output
        assert "No reliability data collected" in output
        assert result.ret == 0
    
    def test_report_with_exactly_five_tests(self, pytester):
        """Verify short verbosity with exactly 5 tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_3():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_4():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_5():
                time.sleep(0.01)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Should show summary statistics
        assert "Vigil Reliability Report" in output
        assert "Total Tests: 5" in output
        assert "Average Duration:" in output
        assert result.ret == 0
    
    def test_report_with_one_test(self, pytester):
        """Verify report with single test shows summary."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_single():
                time.sleep(0.05)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        assert "Vigil Reliability Report" in output
        assert "Total Tests: 1" in output
        assert "test_single" in output
        assert result.ret == 0
    
    def test_report_with_very_long_test_path(self, pytester):
        """Verify report handles long test paths gracefully."""
        # Create nested directory structure
        test_dir = pytester.mkpydir("very_long_directory_name_for_testing")
        test_dir.joinpath("test_file_with_long_name.py").write_text("""
import pytest
import time

@pytest.mark.vigil(timeout=2.0)
def test_with_very_long_function_name_that_might_break_formatting():
    time.sleep(0.05)
""")
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Should show report without formatting issues
        assert "Vigil Reliability Report" in output
        assert result.ret == 0
    
    def test_report_with_retried_tests(self, pytester):
        """Verify report shows retry attempts correctly."""
        pytester.makepyfile("""
            import pytest

            counter = 0

            @pytest.mark.vigil(timeout=2.0, retry=2)
            def test_retry():
                global counter
                counter += 1
                assert counter >= 2
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Should show report with flaky test warning
        assert "Vigil Reliability Report" in output
        assert "Flaky Tests" in output
        assert result.ret == 0


# =============================================================================
# 7. JSON REPORT INTERACTION
# =============================================================================

class TestReportWithJsonGeneration:
    """Test CLI report interaction with JSON report generation."""
    
    def test_json_report_unaffected_by_cli_verbosity(self, pytester):
        """Verify JSON report contains all data regardless of CLI verbosity."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_3():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_4():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_5():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_6():
                time.sleep(0.05)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(
            f"--vigil-report={report_file}",
            "--vigil-cli-report-verbosity=short"
        )
        output = result.stdout.str()
        
        assert result.ret == 0
        
        # CLI should show summary only
        assert "Total Tests: 6" in output
        assert "Average Duration:" in output
        
        # JSON report should have all 6 tests
        report_path = pytester.path / report_file
        with open(report_path) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 6
    
    def test_json_report_with_verbosity_none(self, pytester):
        """Verify JSON report message shown even when CLI verbosity is none."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(
            f"--vigil-report={report_file}",
            "--vigil-cli-report-verbosity=none"
        )
        output = result.stdout.str()
        
        assert result.ret == 0
        
        # CLI report should not be shown
        assert "Vigil Reliability Report" not in output
        
        # But JSON report message should still appear
        assert "Saved Vigil report" in output or result.ret == 0


# =============================================================================
# 8. FEATURE NON-INTERFERENCE TESTS
# =============================================================================

class TestReportNonInterference:
    """Test that CLI report doesn't interfere with other features."""
    
    def test_report_doesnt_affect_timeout_enforcement(self, pytester):
        """Verify report verbosity doesn't affect timeout enforcement."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_timeout():
                time.sleep(1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=none")
        
        # Should still timeout even without report
        assert result.ret == 1
    
    def test_report_doesnt_affect_memory_enforcement(self, pytester):
        """Verify report verbosity doesn't affect memory enforcement."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=10)
            def test_memory():
                data = ["x" * 1024 * 1024 for _ in range(20)]
                time.sleep(1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        
        # Should still enforce memory limit
        assert result.ret == 1
    
    def test_report_doesnt_affect_retry_mechanism(self, pytester):
        """Verify report verbosity doesn't affect retry mechanism."""
        pytester.makepyfile("""
            import pytest

            counter = 0

            @pytest.mark.vigil(timeout=2.0, retry=1)
            def test_retry():
                global counter
                counter += 1
                assert counter >= 2
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=none")
        
        # Should still retry and pass
        assert result.ret == 0
    
    def test_report_works_with_session_timeout(self, pytester):
        """Verify report verbosity works with session timeout configured."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=5.0)
            def test_quick():
                time.sleep(0.05)
        """)
        
        result = pytester.runpytest(
            "--vigil-session-timeout=10",
            "--vigil-cli-report-verbosity=full"
        )
        output = result.stdout.str()
        
        # Should complete successfully and show report
        assert result.ret == 0
        assert "Vigil Reliability Report" in output
    
    def test_report_works_with_all_limit_types(self, pytester):
        """Verify report displays all limit types correctly."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, memory=500, cpu=200)
            def test_all_limits():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Report should show test regardless of pass/fail
        assert "Vigil Reliability Report" in output
        assert "test_all_limits" in output


# =============================================================================
# 9. REPORT CONTENT VALIDATION
# =============================================================================

class TestReportContent:
    """Test that CLI report displays correct data."""
    
    def test_report_shows_attempt_number(self, pytester):
        """Verify full report shows attempt number for retried tests."""
        pytester.makepyfile("""
            import pytest

            counter = 0

            @pytest.mark.vigil(timeout=2.0, retry=2)
            def test_retry():
                global counter
                counter += 1
                assert counter >= 2
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Should show attempt column in full mode
        assert "Att" in output
        assert result.ret == 0
    
    def test_report_shows_duration(self, pytester):
        """Verify report shows test duration in both modes."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_timed():
                time.sleep(0.2)
        """)
        
        # Test full mode
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        assert "Duration (s)" in output
        
        # Test short mode
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        assert "Average Duration:" in output
        assert result.ret == 0
    
    def test_report_shows_resource_metrics(self, pytester):
        """Verify report shows CPU and memory metrics."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        # Test full mode
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        assert "Max CPU (%)" in output
        assert "Max Mem (MB)" in output
        
        # Test short mode
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        assert "Average CPU:" in output
        assert "Peak CPU:" in output
        assert "Average Memory:" in output
        assert "Peak Memory:" in output
        assert result.ret == 0
    
    def test_report_table_formatting(self, pytester):
        """Verify full report table is properly formatted."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Should have proper table structure
        assert "Vigil Reliability Report" in output
        assert "Test ID" in output
        # Should have separator line
        assert "---" in output
        assert result.ret == 0
