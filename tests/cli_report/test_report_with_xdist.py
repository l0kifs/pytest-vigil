"""
Tests for CLI report functionality when running with pytest-xdist parallel execution.
"""

pytest_plugins = ["pytester"]


class TestReportWithXdist:
    """Test CLI report with pytest-xdist parallel execution."""
    
    def test_report_with_xdist_shows_all_tests(self, pytester):
        """Verify report collects results from all xdist workers."""
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
            
            @pytest.mark.vigil(timeout=2.0)
            def test_4():
                time.sleep(0.05)
        """)
        
        result = pytester.runpytest("-n", "2", "--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Report should show all tests
        assert "Vigil Reliability Report" in output
        assert "test_1" in output
        assert "test_4" in output
        assert result.ret == 0
    
    def test_report_verbosity_short_with_xdist(self, pytester):
        """Verify short verbosity works with xdist."""
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
            
            @pytest.mark.vigil(timeout=2.0)
            def test_4():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_5():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_6():
                time.sleep(0.05)
        """)
        
        result = pytester.runpytest("-n", "2", "--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Should show report with summary
        assert "Vigil Reliability Report" in output
        assert "Total Tests:" in output
        assert "Average Duration:" in output
        assert result.ret == 0
    
    def test_report_verbosity_none_with_xdist(self, pytester):
        """Verify verbosity=none works with xdist."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.05)
        """)
        
        result = pytester.runpytest("-n", "2", "--vigil-cli-report-verbosity=none")
        output = result.stdout.str()
        
        # Should not show report
        assert "Vigil Reliability Report" not in output
        assert result.ret == 0
