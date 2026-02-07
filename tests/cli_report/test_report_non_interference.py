"""
Tests for ensuring CLI report non-interference with other features.
"""

pytest_plugins = ["pytester"]


class TestReportNonInterference:
    """Test that CLI report doesn't interfere with other features."""
    
    def test_report_doesnt_affect_timeout_enforcement(self, pytester):
        """Verify report verbosity doesn't affect timeout enforcement."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_timeout():
                time.sleep(1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=none")
        
        # Should still timeout even without report
        assert result.ret == 1
    
    def test_report_doesnt_affect_memory_enforcement(self, pytester):
        """Verify report verbosity doesn't affect memory enforcement."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=10)
            def test_memory():
                data = ["x" * 1024 * 1024 for _ in range(20)]
                time.sleep(1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        
        # Should still enforce memory limit
        assert result.ret == 1
    
    def test_report_doesnt_affect_retry_mechanism(self, pytester):
        """Verify report verbosity doesn't affect retry mechanism."""
        pytester.makepyfile("""
            import pytest

            counter = 0

            @pytest.mark.vigil(timeout=2.0, retry=1)
            def test_retry():
                global counter
                counter += 1
                assert counter >= 2
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=none")
        
        # Should still retry and pass
        assert result.ret == 0
    
    def test_report_works_with_session_timeout(self, pytester):
        """Verify report verbosity works with session timeout configured."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=5.0)
            def test_quick():
                time.sleep(0.05)
        """)
        
        result = pytester.runpytest(
            "--vigil-session-timeout=10",
            "--vigil-cli-report-verbosity=full"
        )
        output = result.stdout.str()
        
        # Should complete successfully and show report
        assert result.ret == 0
        assert "Vigil Reliability Report" in output
    
    def test_report_works_with_all_limit_types(self, pytester):
        """Verify report displays all limit types correctly."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, memory=500, cpu=200)
            def test_all_limits():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Report should show test regardless of pass/fail
        assert "Vigil Reliability Report" in output
        assert "test_all_limits" in output
