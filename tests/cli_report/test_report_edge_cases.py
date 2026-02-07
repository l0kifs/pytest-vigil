"""
Edge case tests for CLI report functionality.
"""

pytest_plugins = ["pytester"]


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
