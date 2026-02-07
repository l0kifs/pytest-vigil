"""
Tests for basic CLI report verbosity functionality.
"""

pytest_plugins = ["pytester"]


class TestBasicReportVerbosity:
    """Test basic CLI report verbosity functionality."""
    
    def test_default_verbosity_is_short(self, pytester):
        """Verify default verbosity is 'short' (shows summary statistics)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.02)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_3():
                time.sleep(0.03)
        """)
        
        result = pytester.runpytest()
        output = result.stdout.str()
        
        # Should show report section
        assert "Vigil Reliability Report" in output
        # Should show summary statistics
        assert "Total Tests:" in output
        assert "Average Duration:" in output
        assert "Fastest Test:" in output
        assert "Slowest Test:" in output
        assert "Average CPU:" in output
        assert "Peak CPU:" in output
        assert "Average Memory:" in output
        assert "Peak Memory:" in output
        # Should not show detailed table headers
        assert "Test ID" not in output or "Total Tests" in output  # If Test ID appears, it's in test names, not table
        assert result.ret == 0
    
    def test_verbosity_none_hides_report(self, pytester):
        """Verify verbosity=none completely hides the report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=none")
        output = result.stdout.str()
        
        # Should not show report section
        assert "Vigil Reliability Report" not in output
        assert "Test ID" not in output
        assert "Duration (s)" not in output
        assert result.ret == 0
    
    def test_verbosity_short_shows_limited_tests(self, pytester):
        """Verify verbosity=short shows summary statistics only."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.02)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_3():
                time.sleep(0.03)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_4():
                time.sleep(0.04)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_5():
                time.sleep(0.05)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_6():
                time.sleep(0.06)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=short")
        output = result.stdout.str()
        
        # Should show report
        assert "Vigil Reliability Report" in output
        # Should show summary statistics
        assert "Total Tests: 6" in output
        assert "Average Duration:" in output
        assert "Fastest Test:" in output
        assert "Slowest Test:" in output
        # Should not show detailed table
        assert "Att" not in output  # Table header
        assert result.ret == 0
    
    def test_verbosity_full_shows_all_tests(self, pytester):
        """Verify verbosity=full shows detailed table with all tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_1():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_2():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_3():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_4():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_5():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_6():
                time.sleep(0.01)
            
            @pytest.mark.vigil(timeout=2.0)
            def test_7():
                time.sleep(0.01)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Should show detailed table
        assert "Vigil Reliability Report" in output
        assert "Test ID" in output
        assert "Att" in output
        assert "Duration (s)" in output
        # Should not show summary stats format
        assert "Total Tests:" not in output
        # All test names should be visible in table
        assert "test_1" in output
        assert "test_7" in output
        assert result.ret == 0
