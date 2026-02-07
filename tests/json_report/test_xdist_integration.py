"""
Tests for JSON report integration with pytest-xdist.
"""

import json

pytest_plugins = ["pytester"]


class TestXDistIntegration:
    """Test JSON report with pytest-xdist."""
    
    def test_report_xdist_aggregation(self, pytester):
        """Verify JSON report aggregates results from all xdist workers."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=5.0)
            def test_worker_1():
                time.sleep(0.1)

            @pytest.mark.vigil(timeout=5.0)
            def test_worker_2():
                time.sleep(0.1)

            @pytest.mark.vigil(timeout=5.0)
            def test_worker_3():
                time.sleep(0.1)

            @pytest.mark.vigil(timeout=5.0)
            def test_worker_4():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_xdist.json"
        result = pytester.runpytest("-n", "2", f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        report_path = pytester.path / report_file
        assert report_path.exists(), "Report file was not created"
        
        with open(report_path) as f:
            data = json.load(f)
        
        # All 4 tests should be in the report
        assert len(data["results"]) == 4
        
        nodeids = [r["node_id"] for r in data["results"]]
        assert any("test_worker_1" in n for n in nodeids)
        assert any("test_worker_2" in n for n in nodeids)
        assert any("test_worker_3" in n for n in nodeids)
        assert any("test_worker_4" in n for n in nodeids)
    
    def test_report_xdist_with_failures(self, pytester):
        """Verify xdist report includes both passed and failed tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=5.0)
            def test_pass_1():
                time.sleep(0.1)

            @pytest.mark.vigil(timeout=5.0)
            def test_fail():
                time.sleep(0.1)
                assert False, "Expected failure"

            @pytest.mark.vigil(timeout=5.0)
            def test_pass_2():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_xdist.json"
        result = pytester.runpytest("-n", "2", f"--vigil-report={report_file}")
        
        assert result.ret == 1  # One failure
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 3
    
    def test_report_xdist_flaky_tests(self, pytester):
        """Verify flaky tests are properly tracked with xdist."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "flaky_xdist.txt"

            @pytest.mark.vigil(timeout=5.0, retry=2)
            def test_flaky():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                assert True
        """)
        
        report_file = "vigil_xdist.json"
        result = pytester.runpytest("-n", "2", f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        # Should have flaky test recorded
        assert len(data["flaky_tests"]) > 0
