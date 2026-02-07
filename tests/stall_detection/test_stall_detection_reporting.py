"""
Test stall detection reporting in JSON reports.
- Verify that stall detection parameters are correctly recorded in the JSON report.
- Confirm that stall violations are captured in the report with the correct limit type.
- Ensure that stall detection works correctly when combined with other limits and that all limits are accurately represented in the report.
- Verify that CLI parameters for stall detection are also reflected in the JSON report.
"""

import json

pytest_plugins = ["pytester"]


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
