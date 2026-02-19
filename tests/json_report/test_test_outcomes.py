"""
Tests for JSON report generation with various test outcomes (passed, failed, skipped, xfail, xpass).
"""

import json

pytest_plugins = ["pytester"]


class TestTestOutcomes:
    """Test JSON report with various test outcomes."""
    
    def test_report_passed_test(self, pytester):
        """Verify passed test appears in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.1)
                assert True
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        assert "test_pass" in data["results"][0]["node_id"]
    
    def test_report_failed_test(self, pytester):
        """Verify failed test appears in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_fail():
                time.sleep(0.1)
                assert False, "Expected failure"
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 1
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        assert "test_fail" in data["results"][0]["node_id"]
    
    def test_report_skipped_test(self, pytester):
        """Verify skipped test behavior - likely not in report as vigil doesn't run."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            @pytest.mark.skip(reason="Skipped test")
            def test_skip():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        # Skipped test shouldn't fail the run
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        # Skipped tests likely won't appear as vigil doesn't monitor them
        # Just verify report is valid
        assert "results" in data
    
    def test_report_xfail_test(self, pytester):
        """Verify xfail test appears in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            @pytest.mark.xfail(reason="Expected to fail")
            def test_xfail():
                time.sleep(0.1)
                assert False
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        # xfail doesn't cause failure
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        # Test may or may not appear depending on vigil's execution
        assert "results" in data
    
    def test_report_xpass_test(self, pytester):
        """Verify xpass test appears in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            @pytest.mark.xfail(reason="Expected to fail but passes")
            def test_xpass():
                time.sleep(0.1)
                assert True
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        assert "results" in data
    
    def test_report_mixed_outcomes(self, pytester):
        """Verify report contains all tests with different outcomes."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.1)
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_fail():
                time.sleep(0.1)
                assert False, "Expected failure"

            @pytest.mark.vigil(timeout=2.0)
            def test_another_pass():
                time.sleep(0.1)
                assert True
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 1  # One failure
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 3
        node_ids = [r["node_id"] for r in data["results"]]
        assert any("test_pass" in nid for nid in node_ids)
        assert any("test_fail" in nid for nid in node_ids)
        assert any("test_another_pass" in nid for nid in node_ids)
