"""
Edge case tests for JSON report functionality.
"""

import json

pytest_plugins = ["pytester"]


class TestEdgeCases:
    """Test edge cases for JSON report functionality."""
    
    def test_report_empty_test_suite(self, pytester):
        """Verify report handles empty test suite."""
        pytester.makepyfile("""
            # No tests
            pass
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        # No tests collected = no report generated (expected behavior)
        report_path = pytester.path / ".pytest_vigil" / report_file
        if report_path.exists():
            # If report exists, it should be empty
            with open(report_path) as f:
                data = json.load(f)
            assert data["results"] == []
            assert data["flaky_tests"] == []
    
    def test_report_tests_without_vigil_marker(self, pytester):
        """Verify report handles tests without vigil marker."""
        pytester.makepyfile("""
            import pytest
            import time

            def test_no_marker():
                time.sleep(0.1)
                assert True
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        report_path = pytester.path / ".pytest_vigil" / report_file
        # Tests without vigil marker won't generate report
        if report_path.exists():
            with open(report_path) as f:
                data = json.load(f)
            assert "results" in data
    
    def test_report_mixed_vigil_and_non_vigil(self, pytester):
        """Verify report handles mix of vigil and non-vigil tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_with_vigil():
                time.sleep(0.1)

            def test_without_vigil():
                time.sleep(0.1)
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_another_vigil():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        # Should have at least the vigil-marked tests
        vigil_tests = [r for r in data["results"] if "vigil" in r["node_id"]]
        assert len(vigil_tests) >= 2
    
    def test_report_with_test_classes(self, pytester):
        """Verify report handles tests in classes."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            class TestClass:
                def test_one(self):
                    time.sleep(0.1)
                
                def test_two(self):
                    time.sleep(0.1)
            
            @pytest.mark.vigil(timeout=2.0)
            class TestAnotherClass:
                def test_three(self):
                    time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 3
    
    def test_report_multiple_test_files(self, pytester):
        """Verify report aggregates results from multiple test files."""
        pytester.makepyfile(test_file1="""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_in_file1():
                time.sleep(0.1)
        """)
        
        pytester.makepyfile(test_file2="""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_in_file2():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 2
        nodeids = [r["node_id"] for r in data["results"]]
        assert any("test_file1" in nid for nid in nodeids)
        assert any("test_file2" in nid for nid in nodeids)
    
    def test_report_with_zero_measurements(self, pytester):
        """Verify report handles tests with zero resource measurements."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(timeout=2.0)
            def test_instant():
                # Very fast test
                assert True
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        # Should handle tests with minimal measurements
        assert len(data["results"]) == 1
        assert "max_cpu" in data["results"][0]
        assert "max_memory" in data["results"][0]
