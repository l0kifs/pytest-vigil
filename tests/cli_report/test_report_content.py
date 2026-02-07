"""
Tests for CLI report content validation.
"""

pytest_plugins = ["pytester"]


class TestReportContent:
    """Test that CLI report displays correct data."""
    
    def test_report_shows_attempt_number(self, pytester):
        """Verify full report shows attempt number for retried tests."""
        pytester.makepyfile("""
            import pytest

            counter = 0

            @pytest.mark.vigil(timeout=2.0, retry=2)
            def test_retry():
                global counter
                counter += 1
                assert counter >= 2
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Should show attempt column in full mode
        assert "Att" in output
        assert result.ret == 0
    
    def test_report_shows_duration(self, pytester):
        """Verify report shows test duration in both modes."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_timed():
                time.sleep(0.2)
        """)
        
        # Test full mode
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        assert "Duration (s)" in output
        
        # Test short mode
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        assert "Average Duration:" in output
        assert result.ret == 0
    
    def test_report_shows_resource_metrics(self, pytester):
        """Verify report shows CPU and memory metrics."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        # Test full mode
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        assert "Max CPU (%)" in output
        assert "Max Mem (MB)" in output
        
        # Test short mode
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        assert "Average CPU:" in output
        assert "Peak CPU:" in output
        assert "Average Memory:" in output
        assert "Peak Memory:" in output
        assert result.ret == 0
    
    def test_report_table_formatting(self, pytester):
        """Verify full report table is properly formatted."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Should have proper table structure
        assert "Vigil Reliability Report" in output
        assert "Test ID" in output
        # Should have separator line
        assert "---" in output
        assert result.ret == 0
