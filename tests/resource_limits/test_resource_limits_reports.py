"""

"""

import json

pytest_plugins = ["pytester"]


class TestResourceLimitsReports:
    """Test JSON report generation with resource limits."""
    
    def test_report_with_timeout(self, pytester):
        """Verify timeout limit appears in JSON report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.5)
            def test_with_timeout():
                time.sleep(0.1)
                assert True
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        assert "test_with_timeout" in data["results"][0]["node_id"]
        # Check limits are recorded
        limits = data["results"][0]["limits"]
        assert any(limit["limit_type"] == "time" for limit in limits)

    def test_report_with_memory(self, pytester):
        """Verify memory limit appears in JSON report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=150)
            def test_with_memory():
                data = ["x" * 1024 for _ in range(10)]
                time.sleep(0.1)
                assert True
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        limits = data["results"][0]["limits"]
        assert any(limit["limit_type"] == "memory" for limit in limits)

    def test_report_with_cpu(self, pytester):
        """Verify CPU limit appears in JSON report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=200)
            def test_with_cpu():
                time.sleep(0.1)
                result = sum(range(100))
                assert result > 0
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        limits = data["results"][0]["limits"]
        assert any(limit["limit_type"] == "cpu" for limit in limits)

    def test_report_with_all_limits(self, pytester):
        """Verify all limits appear in JSON report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, memory=150, cpu=200)
            def test_all_limits():
                time.sleep(0.1)
                data = ["x" * 1024 for _ in range(5)]
                result = sum(range(50))
                assert result > 0
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        limits = data["results"][0]["limits"]
        limit_types = [limit["limit_type"] for limit in limits]
        assert "time" in limit_types
        assert "memory" in limit_types
        assert "cpu" in limit_types

    def test_report_violation_details(self, pytester):
        """Verify violation details appear in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_violation():
                time.sleep(2)
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        assert result.ret == 1
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        # Check that violation information is captured
        assert data["results"][0]["duration"] > 0

    def test_report_cli_limits(self, pytester):
        """Verify CLI-specified limits appear in report."""
        pytester.makepyfile("""
            import time
            
            def test_cli_limits():
                time.sleep(0.1)
                assert True
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}", "--vigil-timeout=2.0")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 1
        limits = data["results"][0]["limits"]
        assert any(limit["limit_type"] == "time" for limit in limits)

    def test_report_xdist_aggregation(self, pytester):
        """Verify report aggregates results from xdist workers."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_worker_1():
                time.sleep(0.1)

            @pytest.mark.vigil(timeout=1.0)
            def test_worker_2():
                time.sleep(0.1)

            @pytest.mark.vigil(timeout=1.0)
            def test_worker_3():
                time.sleep(0.1)
        """)
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}", "-n", "2")
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        # Should have all 3 tests in report
        assert len(data["results"]) == 3
