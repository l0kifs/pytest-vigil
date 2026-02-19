"""
Tests for CLI report interaction with JSON report generation.
"""
import json

pytest_plugins = ["pytester"]


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
            f"--vigil-json-report={report_file}",
            "--vigil-cli-report-verbosity=short"
        )
        output = result.stdout.str()
        
        assert result.ret == 0
        
        # CLI should show summary only
        assert "Total Tests: 6" in output
        assert "Average Duration:" in output
        
        # JSON report should have all 6 tests
        report_path = pytester.path / ".pytest_vigil" / report_file
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
            f"--vigil-json-report={report_file}",
            "--vigil-cli-report-verbosity=none"
        )
        output = result.stdout.str()
        
        assert result.ret == 0
        
        # CLI report should not be shown
        assert "Vigil Reliability Report" not in output
        
        # But JSON report message should still appear
        assert "Saved Vigil report" in output or result.ret == 0
