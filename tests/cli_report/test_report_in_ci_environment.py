"""
Tests for CLI report behavior in CI environments.
"""

pytest_plugins = ["pytester"]


class TestReportInCIEnvironment:
    """Test CLI report behavior in CI environment."""
    
    def test_report_works_in_ci_environment(self, pytester, monkeypatch):
        """Verify report displays correctly in CI environment."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        # Simulate CI environment
        monkeypatch.setenv("CI", "true")
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Report should still work in CI
        assert "Vigil Reliability Report" in output
        assert "test_sample" in output
        assert result.ret == 0
    
    def test_report_verbosity_none_useful_in_ci(self, pytester, monkeypatch):
        """Verify verbosity=none is useful in CI to reduce log noise."""
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
        
        monkeypatch.setenv("CI", "true")
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=none")
        output = result.stdout.str()
        
        # No report should be shown
        assert "Vigil Reliability Report" not in output
        assert result.ret == 0
