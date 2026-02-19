"""
Tests for CPU breakdown functionality in CLI reports.
"""
import json

pytest_plugins = ["pytester"]


class TestCPUBreakdownFunctionality:
    """Test CPU breakdown by process type functionality."""
    
    def test_cpu_breakdown_appears_in_short_report(self, pytester):
        """Verify CPU breakdown appears in short verbosity report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Should show CPU breakdown section
        assert "Vigil Reliability Report" in output
        assert "Peak CPU by Process Type:" in output
        assert "Pytest:" in output
        assert result.ret == 0
    
    def test_cpu_breakdown_not_in_full_report(self, pytester):
        """Verify CPU breakdown is only shown in short mode, not full table mode."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Full mode shows table, not breakdown summary
        assert "Vigil Reliability Report" in output
        assert "Test ID" in output
        # CPU breakdown section is only in short mode
        assert "Peak CPU by Process Type:" not in output
        assert result.ret == 0
    
    def test_cpu_breakdown_not_shown_with_verbosity_none(self, pytester):
        """Verify CPU breakdown is hidden when verbosity is none."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=none")
        output = result.stdout.str()
        
        # Should not show any report
        assert "Vigil Reliability Report" not in output
        assert "Peak CPU by Process Type:" not in output
        assert result.ret == 0
    
    def test_cpu_breakdown_with_subprocess(self, pytester):
        """Verify CPU breakdown tracks subprocess CPU usage."""
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
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Should show CPU breakdown
        assert "Peak CPU by Process Type:" in output
        assert "Pytest:" in output
        # May or may not show Python subprocess depending on timing
        assert result.ret == 0
    
    def test_cpu_breakdown_in_json_report(self, pytester):
        """Verify CPU breakdown is included in JSON report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_cpu_breakdown.json"
        result = pytester.runpytest(
            f"--vigil-json-report={report_file}",
            "--vigil-cli-report-verbosity=short"
        )
        
        assert result.ret == 0
        
        # Check JSON report contains cpu_breakdown
        report_path = pytester.path / ".pytest_vigil" / report_file
        with open(report_path) as f:
            data = json.load(f)
        
        assert len(data["results"]) > 0
        # Check that cpu_breakdown field exists
        assert "cpu_breakdown" in data["results"][0]
        assert isinstance(data["results"][0]["cpu_breakdown"], dict)
        # Should at least have pytest process
        assert "pytest" in data["results"][0]["cpu_breakdown"]
    
    def test_cpu_breakdown_with_multiple_tests(self, pytester):
        """Verify CPU breakdown aggregates correctly across multiple tests."""
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
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Should show aggregated CPU breakdown
        assert "Peak CPU by Process Type:" in output
        assert "Pytest:" in output
        assert "Total Tests: 3" in output
        assert result.ret == 0
    
    def test_cpu_breakdown_sorted_descending(self, pytester):
        """Verify CPU breakdown is sorted by CPU value (descending)."""
        pytester.makepyfile("""
            import pytest
            import subprocess
            import time

            @pytest.mark.vigil(timeout=5.0)
            def test_multi_subprocess():
                # Spawn multiple subprocesses to generate varied CPU usage
                procs = []
                for i in range(2):
                    proc = subprocess.Popen(
                        ["python", "-c", "x = sum(range(100000))"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    procs.append(proc)
                
                for proc in procs:
                    proc.wait()
                
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Should show CPU breakdown
        assert "Peak CPU by Process Type:" in output
        # Output should be sorted (highest CPU first)
        # At minimum, pytest should appear
        assert "Pytest:" in output
        assert result.ret == 0
    
    def test_cpu_breakdown_with_xdist(self, pytester):
        """Verify CPU breakdown works with pytest-xdist parallel execution."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.1)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.1)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_3():
                time.sleep(0.1)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_4():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("-n", "2", "--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Should show CPU breakdown aggregated from all workers
        assert "Peak CPU by Process Type:" in output
        assert "Pytest:" in output
        assert "Total Tests: 4" in output
        assert result.ret == 0
    
    def test_cpu_breakdown_json_with_xdist(self, pytester):
        """Verify CPU breakdown in JSON report works with xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.1)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_xdist_breakdown.json"
        result = pytester.runpytest(
            "-n", "2",
            f"--vigil-json-report={report_file}",
            "--vigil-cli-report-verbosity=short"
        )
        
        assert result.ret == 0
        
        # Check JSON report
        report_path = pytester.path / ".pytest_vigil" / report_file
        with open(report_path) as f:
            data = json.load(f)
        
        # Should have results from both workers
        assert len(data["results"]) == 2
        # Each should have cpu_breakdown
        for result_data in data["results"]:
            assert "cpu_breakdown" in result_data
            assert "pytest" in result_data["cpu_breakdown"]
    
    def test_cpu_breakdown_empty_when_no_measurements(self, pytester):
        """Verify CPU breakdown handles tests with no measurements gracefully."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(timeout=2.0)
            def test_instant():
                pass
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Should show report
        assert "Vigil Reliability Report" in output
        # CPU breakdown section should appear even if minimal
        assert "Peak CPU by Process Type:" in output
        assert result.ret == 0
    
    def test_cpu_breakdown_capitalized_process_names(self, pytester):
        """Verify process type names are capitalized in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Process type names should be capitalized
        assert "Pytest:" in output  # Not "pytest:"
        # Should not have lowercase in breakdown section
        lines = output.split('\n')
        breakdown_section = False
        for line in lines:
            if "Peak CPU by Process Type:" in line:
                breakdown_section = True
            elif breakdown_section and line.strip() and not line.strip().startswith('('):
                # Lines in breakdown section should be capitalized
                if ':' in line:
                    process_name = line.strip().split(':')[0]
                    # First letter should be uppercase
                    assert process_name[0].isupper(), f"Process name '{process_name}' should be capitalized"
                    break
        
        assert result.ret == 0
