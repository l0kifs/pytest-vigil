"""
Tests for CLI report configuration via environment variables and CLI options.
"""

pytest_plugins = ["pytester"]


class TestReportConfiguration:
    """Test CLI report configuration via environment and CLI."""
    
    def test_env_variable_sets_verbosity(self, pytester, monkeypatch):
        """Verify PYTEST_VIGIL__CONSOLE_REPORT_VERBOSITY environment variable works."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        # Set environment variable
        monkeypatch.setenv("PYTEST_VIGIL__CONSOLE_REPORT_VERBOSITY", "none")
        
        result = pytester.runpytest()
        output = result.stdout.str()
        
        # Should not show report
        assert "Vigil Reliability Report" not in output
        assert result.ret == 0
    
    def test_cli_overrides_env_variable(self, pytester, monkeypatch):
        """Verify CLI option overrides environment variable."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        # Set env to none
        monkeypatch.setenv("PYTEST_VIGIL__CONSOLE_REPORT_VERBOSITY", "none")
        
        # Override with CLI
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Should show report (CLI wins)
        assert "Vigil Reliability Report" in output
        assert result.ret == 0
    
    def test_invalid_verbosity_value_rejected(self, pytester):
        """Verify invalid verbosity values are rejected."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_sample():
                time.sleep(0.1)
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=invalid")
        
        # Should fail with error about invalid choice
        assert result.ret == 4  # pytest error code for usage error
