"""
Tests for JSON report retry mechanism.
"""

import json

pytest_plugins = ["pytester"]


class TestRetryMechanism:
    """Test JSON report with retry mechanism."""
    
    def test_report_multiple_attempts(self, pytester):
        """Verify multiple attempts are recorded in report."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "flaky.txt"

            @pytest.mark.vigil(timeout=2.0, retry=2)
            def test_flaky():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First attempt fails"
                assert True
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        # Should have multiple attempts for the flaky test
        test_results = [r for r in data["results"] if "test_flaky" in r["node_id"]]
        assert len(test_results) > 1
        
        # Verify attempt numbers
        attempts = [r["attempt"] for r in test_results]
        assert 0 in attempts  # First attempt
        assert max(attempts) > 0  # At least one retry
    
    def test_report_flaky_tests_list(self, pytester):
        """Verify flaky tests are listed in report."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "flaky.txt"

            @pytest.mark.vigil(timeout=2.0, retry=2)
            def test_flaky():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First attempt fails"
                assert True
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        assert len(data["flaky_tests"]) > 0
        assert any("test_flaky" in nodeid for nodeid in data["flaky_tests"])
    
    def test_report_no_flaky_tests(self, pytester):
        """Verify flaky_tests list is empty when no flaky tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, retry=2)
            def test_stable():
                time.sleep(0.1)
                assert True
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        assert len(data["flaky_tests"]) == 0
