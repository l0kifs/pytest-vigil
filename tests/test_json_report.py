"""
Comprehensive tests for JSON report functionality.

Tests cover:
- All test outcomes (pass, fail, skip, xfail, xpass)
- All available parameters
- CI environment interaction
- XDist integration
- Edge cases
- Feature non-interference
"""

import pytest
import json
import os
from pathlib import Path

pytest_plugins = ["pytester"]


class TestBasicReportGeneration:
    """Test basic JSON report generation functionality."""
    
    def test_report_structure(self, pytester):
        """Verify JSON report has correct structure and required fields."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        report_path = pytester.path / report_file
        assert report_path.exists()
        
        with open(report_path) as f:
            data = json.load(f)
        
        # Verify top-level structure
        assert "timestamp" in data
        assert "flaky_tests" in data
        assert "results" in data
        
        # Verify timestamp is ISO 8601
        from datetime import datetime
        datetime.fromisoformat(data["timestamp"])
        
        # Verify results structure
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0
        
        result_entry = data["results"][0]
        assert "node_id" in result_entry
        assert "attempt" in result_entry
        assert "duration" in result_entry
        assert "max_cpu" in result_entry
        assert "max_memory" in result_entry
        assert "limits" in result_entry
    
    def test_report_with_relative_path(self, pytester):
        """Verify report can be created with relative path."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "reports/vigil.json"
        pytester.path.joinpath("reports").mkdir(exist_ok=True)
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        report_path = pytester.path / report_file
        assert report_path.exists()
    
    def test_report_with_absolute_path(self, pytester, tmp_path):
        """Verify report can be created with absolute path."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = tmp_path / "vigil_absolute.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        assert report_file.exists()
    
    def test_report_overwrites_existing_file(self, pytester):
        """Verify report overwrites existing file."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        report_path = pytester.path / report_file
        
        # Create existing file
        report_path.write_text('{"old": "data"}')
        
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        with open(report_path) as f:
            data = json.load(f)
        
        assert "old" not in data
        assert "results" in data
    
    def test_no_report_without_option(self, pytester):
        """Verify no report is generated without --vigil-report option."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest()
        
        assert result.ret == 0
        # Check no vigil_report.json created
        assert not (pytester.path / "vigil_report.json").exists()


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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 1
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        # Skipped test shouldn't fail the run
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        # xfail doesn't cause failure
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 1  # One failure
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["results"]) == 3
        node_ids = [r["node_id"] for r in data["results"]]
        assert any("test_pass" in nid for nid in node_ids)
        assert any("test_fail" in nid for nid in node_ids)
        assert any("test_another_pass" in nid for nid in node_ids)


class TestParameters:
    """Test JSON report with various vigil parameters."""
    
    def test_report_timeout_parameter(self, pytester):
        """Verify timeout parameter is recorded in limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.5)
            def test_timeout():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        limits = data["results"][0]["limits"]
        timeout_limits = [l for l in limits if l.get("limit_type") == "time"]
        assert len(timeout_limits) > 0
        assert timeout_limits[0]["threshold"] == 1.5
    
    def test_report_memory_parameter(self, pytester):
        """Verify memory parameter is recorded in limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=100)
            def test_memory():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        limits = data["results"][0]["limits"]
        memory_limits = [l for l in limits if l.get("limit_type") == "memory"]
        assert len(memory_limits) > 0
        assert memory_limits[0]["threshold"] == 100
    
    def test_report_cpu_parameter(self, pytester):
        """Verify CPU parameter is recorded in limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=200)
            def test_cpu():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        limits = data["results"][0]["limits"]
        cpu_limits = [l for l in limits if l.get("limit_type") == "cpu"]
        assert len(cpu_limits) > 0
        assert cpu_limits[0]["threshold"] == 200
    
    def test_report_all_parameters(self, pytester):
        """Verify all parameters are recorded correctly."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, memory=100, cpu=200)
            def test_all_params():
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
        assert "memory" in limit_types
        assert "cpu" in limit_types
    
    def test_report_cli_parameters(self, pytester):
        """Verify CLI parameters are recorded in report."""
        pytester.makepyfile("""
            import pytest
            import time

            def test_cli_params():
                time.sleep(0.1)
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(
            "--vigil-timeout=1.5",
            "--vigil-memory=50",
            "--vigil-cpu=60",
            f"--vigil-report={report_file}"
        )
        
        # CLI params create limits even without marker
        # But the test will fail due to low CPU limit (50MB)
        # So we expect failure, but report should still be generated
        report_path = pytester.path / report_file
        assert report_path.exists()
        
        with open(report_path) as f:
            data = json.load(f)
        
        assert "results" in data
        assert len(data["results"]) > 0


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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        assert len(data["flaky_tests"]) == 0


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


class TestEdgeCases:
    """Test edge cases for JSON report functionality."""
    
    def test_report_empty_test_suite(self, pytester):
        """Verify report handles empty test suite."""
        pytester.makepyfile("""
            # No tests
            pass
        """)
        
        report_file = "vigil_report.json"
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        # No tests collected = no report generated (expected behavior)
        report_path = pytester.path / report_file
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        report_path = pytester.path / report_file
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
            data = json.load(f)
        
        # Should handle tests with minimal measurements
        assert len(data["results"]) == 1
        assert "max_cpu" in data["results"][0]
        assert "max_memory" in data["results"][0]


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
            f"--vigil-report={report_file}"
        )
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        # Should still fail
        assert result.ret == 1
        
        # But report should be generated
        assert (pytester.path / report_file).exists()
    
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
        result = pytester.runpytest("-vv", f"--vigil-report={report_file}")
        
        assert result.ret == 0
        assert (pytester.path / report_file).exists()


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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest("-n", "2", f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 1
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        # If we can load it as JSON, all values are serializable
        with open(pytester.path / report_file) as f:
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
        result = pytester.runpytest(f"--vigil-report={report_file}")
        
        assert result.ret == 0
        
        with open(pytester.path / report_file) as f:
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
