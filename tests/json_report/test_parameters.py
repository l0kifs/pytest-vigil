"""
Tests for JSON report generation with various parameters.
"""

import json

pytest_plugins = ["pytester"]


class TestParameters:
    """Test JSON report with various vigil parameters."""
    
    def test_report_timeout_parameter(self, pytester):
        """Verify timeout parameter is recorded in limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.5)
            def test_timeout():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        limits = data["results"][0]["limits"]
        timeout_limits = [l for l in limits if l.get("limit_type") == "time"]
        assert len(timeout_limits) > 0
        assert timeout_limits[0]["threshold"] == 1.5
    
    def test_report_memory_parameter(self, pytester):
        """Verify memory parameter is recorded in limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=100)
            def test_memory():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        limits = data["results"][0]["limits"]
        memory_limits = [l for l in limits if l.get("limit_type") == "memory"]
        assert len(memory_limits) > 0
        assert memory_limits[0]["threshold"] == 100
    
    def test_report_cpu_parameter(self, pytester):
        """Verify CPU parameter is recorded in limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=200)
            def test_cpu():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        limits = data["results"][0]["limits"]
        cpu_limits = [l for l in limits if l.get("limit_type") == "cpu"]
        assert len(cpu_limits) > 0
        assert cpu_limits[0]["threshold"] == 200
    
    def test_report_all_parameters(self, pytester):
        """Verify all parameters are recorded correctly."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, memory=100, cpu=200)
            def test_all_params():
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
        assert "memory" in limit_types
        assert "cpu" in limit_types
    
    def test_report_cli_parameters(self, pytester):
        """Verify CLI parameters are recorded in report."""
        pytester.makepyfile("""
            import pytest
            import time

            def test_cli_params():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(
            "--vigil-timeout=1.5",
            "--vigil-memory=50",
            "--vigil-cpu=60",
            f"--vigil-report={report_file}"
        )
        
        # CLI params create limits even without marker
        # But the test will fail due to low CPU limit (50MB)
        # So we expect failure, but report should still be generated
        report_path = pytester.path / report_file
        assert report_path.exists()
        
        with open(report_path) as f:
            data = json.load(f)
        
        assert "results" in data
        assert len(data["results"]) > 0
