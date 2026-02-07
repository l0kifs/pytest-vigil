"""
Tests for basic JSON report generation.
"""
import json

pytest_plugins = ["pytester"]


class TestBasicReportGeneration:
    """Test basic JSON report generation functionality."""
    
    def test_report_structure(self, pytester):
        """Verify JSON report has correct structure and required fields."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        report_path = pytester.path / report_file
        assert report_path.exists()
        
        with open(report_path) as f:
            data = json.load(f)
        
        # Verify top-level structure
        assert "timestamp" in data
        assert "flaky_tests" in data
        assert "results" in data
        
        # Verify timestamp is ISO 8601
        from datetime import datetime
        datetime.fromisoformat(data["timestamp"])
        
        # Verify results structure
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0
        
        result_entry = data["results"][0]
        assert "node_id" in result_entry
        assert "attempt" in result_entry
        assert "duration" in result_entry
        assert "max_cpu" in result_entry
        assert "max_memory" in result_entry
        assert "limits" in result_entry
    
    def test_report_with_relative_path(self, pytester):
        """Verify report can be created with relative path."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "reports/vigil.json"
        pytester.path.joinpath("reports").mkdir(exist_ok=True)
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        report_path = pytester.path / report_file
        assert report_path.exists()
    
    def test_report_with_absolute_path(self, pytester, tmp_path):
        """Verify report can be created with absolute path."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = tmp_path / "vigil_absolute.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        assert report_file.exists()
    
    def test_report_overwrites_existing_file(self, pytester):
        """Verify report overwrites existing file."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        report_path = pytester.path / report_file
        
        # Create existing file
        report_path.write_text('{"old": "data"}')
        
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        with open(report_path) as f:
            data = json.load(f)
        
        assert "old" not in data
        assert "results" in data
    
    def test_no_report_without_option(self, pytester):
        """Verify no report is generated without --vigil-report option."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest()
        
        assert result.ret == 0
        # Check no vigil_report.json created
        assert not (pytester.path / "vigil_report.json").exists()
