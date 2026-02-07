"""
Tests for retry parameter precedence and configuration.
"""

pytest_plugins = ["pytester"]


class TestRetryParameters:
    """Test retry parameter precedence and configuration."""
    
    def test_parameter_precedence_marker_over_cli(self, pytester):
        """Verify marker parameter overrides CLI parameter."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "precedence.txt"

            @pytest.mark.vigil(retry=3)
            def test_precedence():
                # Will use marker retry=3, not CLI retry=1
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                elif os.path.getsize(FILENAME) < 2:
                    with open(FILENAME, "a") as f:
                        f.write("2")
                    assert False
                else:
                    assert True
        """)
        
        # CLI says retry=1, but marker says retry=3
        result = pytester.runpytest("--vigil-retry=1")
        assert result.ret == 0  # Would fail with only 1 retry
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
    
    def test_parameter_precedence_cli_over_env(self, pytester, monkeypatch):
        """Verify CLI parameter overrides environment variable."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "cli_over_env.txt"

            @pytest.mark.vigil(timeout=2.0)
            def test_cli_over_env():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        
        # Env says retry=0, but CLI says retry=2
        monkeypatch.setenv("PYTEST_VIGIL__RETRY_COUNT", "0")
        result = pytester.runpytest("--vigil-retry=2")
        
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
