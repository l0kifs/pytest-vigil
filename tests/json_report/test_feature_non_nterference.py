"""
Tests to ensure JSON report generation does not interfere with other features.
"""

import json

pytest_plugins = ["pytester"]


class TestFeatureNonInterference:
    """Test that JSON report doesn't interfere with other features."""
    
    def test_report_with_session_timeout(self, pytester):
        """Verify JSON report works with session timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_with_session_timeout():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(
            "--vigil-session-timeout=10",
            f"--vigil-json-report={report_file}"
        )
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
    
    def test_report_preserves_exit_code(self, pytester):
        """Verify report generation doesn't change exit codes."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_fail_preserve_exit():
                time.sleep(0.1)
                assert False, "Expected failure"
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        # Should still fail
        assert result.ret == 1
        
        # But report should be generated
        assert (pytester.path / ".pytest_vigil" / report_file).exists()
    
    def test_report_with_verbose_output(self, pytester):
        """Verify report works with verbose pytest output."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_verbose():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest("-vv", f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        assert (pytester.path / ".pytest_vigil" / report_file).exists()
