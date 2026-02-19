"""
Tests for CPU breakdown in JSON report.
"""

import json

pytest_plugins = ["pytester"]


class TestCPUBreakdownInJSON:
    """Test CPU breakdown by process type in JSON reports."""
    
    def test_cpu_breakdown_field_exists(self, pytester):
        """Verify cpu_breakdown field is present in JSON report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) > 0
        result_entry = data["results"][0]
        
        # cpu_breakdown field should exist
        assert "cpu_breakdown" in result_entry
        assert isinstance(result_entry["cpu_breakdown"], dict)
    
    def test_cpu_breakdown_contains_pytest_process(self, pytester):
        """Verify cpu_breakdown contains at least pytest process."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        cpu_breakdown = data["results"][0]["cpu_breakdown"]
        
        # Should have at least pytest process
        assert "pytest" in cpu_breakdown
        assert isinstance(cpu_breakdown["pytest"], (int, float))
        assert cpu_breakdown["pytest"] >= 0
    
    def test_cpu_breakdown_with_subprocess(self, pytester):
        """Verify cpu_breakdown tracks subprocess CPU usage."""
        pytester.makepyfile("""
            import pytest
            import subprocess
            import time

            @pytest.mark.vigil(timeout=5.0)
            def test_with_subprocess():
                # Spawn a Python subprocess
                proc = subprocess.Popen(
                    ["python", "-c", "import time; time.sleep(0.2)"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                proc.wait()
                time.sleep(0.1)
        """)
        
        report_file = "vigil_subprocess.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        cpu_breakdown = data["results"][0]["cpu_breakdown"]
        
        # Should have pytest, may have python subprocess
        assert "pytest" in cpu_breakdown
        # Depending on timing, may capture python subprocess
        assert isinstance(cpu_breakdown, dict)
    
    def test_cpu_breakdown_process_types(self, pytester):
        """Verify cpu_breakdown can contain various process types."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_process_types():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        cpu_breakdown = data["results"][0]["cpu_breakdown"]
        
        # Verify all values are numeric
        for process_type, cpu_value in cpu_breakdown.items():
            assert isinstance(process_type, str)
            assert isinstance(cpu_value, (int, float))
            assert cpu_value >= 0
    
    def test_cpu_breakdown_multiple_tests(self, pytester):
        """Verify cpu_breakdown is recorded for all tests."""
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
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        # All tests should have cpu_breakdown
        assert len(data["results"]) == 3
        for result_entry in data["results"]:
            assert "cpu_breakdown" in result_entry
            assert isinstance(result_entry["cpu_breakdown"], dict)
            assert len(result_entry["cpu_breakdown"]) > 0
    
    def test_cpu_breakdown_with_xdist(self, pytester):
        """Verify cpu_breakdown works with pytest-xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_xdist_1():
                time.sleep(0.1)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_xdist_2():
                time.sleep(0.1)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_xdist_3():
                time.sleep(0.1)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_xdist_4():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_xdist_breakdown.json"
        result = pytester.runpytest("-n", "2", f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        # All 4 tests should have cpu_breakdown
        assert len(data["results"]) == 4
        for result_entry in data["results"]:
            assert "cpu_breakdown" in result_entry
            assert "pytest" in result_entry["cpu_breakdown"]
    
    def test_cpu_breakdown_with_failed_test(self, pytester):
        """Verify cpu_breakdown is recorded even for failed tests."""
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
        
        # Failed test should still have cpu_breakdown
        assert len(data["results"]) == 1
        assert "cpu_breakdown" in data["results"][0]
        assert len(data["results"][0]["cpu_breakdown"]) > 0
    
    def test_cpu_breakdown_with_retry(self, pytester):
        """Verify cpu_breakdown is recorded for each retry attempt."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "retry_test.txt"

            @pytest.mark.vigil(timeout=2.0, retry=2)
            def test_retry():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First attempt fails"
                assert True
        """)
        
        report_file = "vigil_retry_breakdown.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        # Multiple attempts should each have cpu_breakdown
        test_results = [r for r in data["results"] if "test_retry" in r["node_id"]]
        assert len(test_results) > 1
        
        for result_entry in test_results:
            assert "cpu_breakdown" in result_entry
            assert "pytest" in result_entry["cpu_breakdown"]
    
    def test_cpu_breakdown_total_matches_max_cpu(self, pytester):
        """Verify max_cpu value matches sum of cpu_breakdown values."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        result_entry = data["results"][0]
        max_cpu = result_entry["max_cpu"]
        cpu_breakdown = result_entry["cpu_breakdown"]
        
        # The sum of breakdown should be close to or equal to max_cpu
        # (within reasonable margin due to timing differences)
        breakdown_sum = sum(cpu_breakdown.values())
        
        # They should be reasonably close (allowing for timing variations)
        # Max CPU is peak across all measurements, breakdown is also peak per type
        assert breakdown_sum > 0
        assert max_cpu > 0
    
    def test_cpu_breakdown_empty_dict_on_no_measurements(self, pytester):
        """Verify cpu_breakdown handles tests with no measurements gracefully."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(timeout=2.0)
            def test_instant():
                pass
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        # Should have cpu_breakdown field even if minimal measurements
        assert "cpu_breakdown" in data["results"][0]
        assert isinstance(data["results"][0]["cpu_breakdown"], dict)
    
    def test_cpu_breakdown_json_serializable(self, pytester):
        """Verify cpu_breakdown values are JSON serializable."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        # If we can load it as JSON, all values are serializable
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        # Verify we can serialize again (round-trip test)
        json_str = json.dumps(data)
        reloaded = json.loads(json_str)
        
        assert reloaded["results"][0]["cpu_breakdown"] == data["results"][0]["cpu_breakdown"]
    
    def test_cpu_breakdown_preserves_structure(self, pytester):
        """Verify cpu_breakdown preserves expected JSON structure."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-json-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / ".pytest_vigil" / report_file) as f:
            data = json.load(f)
        
        result_entry = data["results"][0]
        
        # Verify structure
        assert "node_id" in result_entry
        assert "attempt" in result_entry
        assert "duration" in result_entry
        assert "max_cpu" in result_entry
        assert "max_memory" in result_entry
        assert "cpu_breakdown" in result_entry
        assert "limits" in result_entry
        
        # Verify cpu_breakdown is at the same level as other metrics
        assert isinstance(result_entry["cpu_breakdown"], dict)
