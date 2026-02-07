"""
Tests for JSON report behavior in CI environment.
"""

import json
import pytest

pytest_plugins = ["pytester"]


class TestCIEnvironment:
    """Test JSON report behavior in CI environment."""
    
    def test_report_ci_multiplier_applied(self, pytester):
        """Verify CI multiplier is reflected in report limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_ci():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        
        # Run with CI=true
        with pytest.MonkeyPatch.context() as m:
            m.setenv("CI", "true")
            result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        limits = data["results"][0]["limits"]
        timeout_limits = [l for l in limits if l.get("limit_type") == "time"]
        # CI multiplier (default 2.0) should be applied: 1.0 * 2.0 = 2.0
        assert len(timeout_limits) > 0
        assert timeout_limits[0]["threshold"] == 2.0
    
    def test_report_no_ci_multiplier(self, pytester):
        """Verify no CI multiplier when CI=false."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_no_ci():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        
        # Run without CI
        with pytest.MonkeyPatch.context() as m:
            m.setenv("CI", "false")
            result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        limits = data["results"][0]["limits"]
        timeout_limits = [l for l in limits if l.get("limit_type") == "time"]
        # No multiplier: original value
        assert len(timeout_limits) > 0
        assert timeout_limits[0]["threshold"] == 1.0
