"""
Test basic retry mechanism functionality.
- Verify that flaky tests are retried based on marker, CLI, and environment variable parameters.
- Ensure that tests are not retried by default and that retry=0 disables retries.
"""

pytest_plugins = ["pytester"]


class TestBasicRetryMechanism:
    """Test basic retry mechanism functionality."""
    
    def test_retry_mechanism_marker(self, pytester):
        """Verify that flaky tests are retried with marker parameter."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "flaky_marker.txt"

            @pytest.mark.vigil(retry=2)
            def test_flaky():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First run fails"
                else:
                    assert True
        """)
        
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Detected Flaky Tests (Passed on Retry):*",
            "*test_flaky*"
        ])
        assert result.ret == 0
    
    def test_retry_mechanism_cli(self, pytester):
        """Verify retry works with CLI parameter."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "flaky_cli.txt"

            @pytest.mark.vigil(timeout=2.0)
            def test_flaky_cli():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First run fails"
                else:
                    assert True
        """)
        
        result = pytester.runpytest("--vigil-retry=2")
        
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
        assert result.ret == 0
    
    def test_retry_mechanism_env(self, pytester, monkeypatch):
        """Verify retry works with environment variable."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "flaky_env.txt"

            @pytest.mark.vigil(timeout=2.0)
            def test_flaky_env():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First run fails"
                else:
                    assert True
        """)
        
        monkeypatch.setenv("PYTEST_VIGIL__RETRY_COUNT", "2")
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
        assert result.ret == 0
    
    def test_no_retry_by_default(self, pytester):
        """Verify tests are not retried by default."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(timeout=2.0)
            def test_fail():
                assert False, "This should fail"
        """)
        
        result = pytester.runpytest()
        
        # Should fail without retry
        assert result.ret == 1
        # Should NOT show flaky test message
        assert "Detected Flaky Tests" not in result.stdout.str()
    
    def test_retry_zero(self, pytester):
        """Verify retry=0 disables retry mechanism."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "no_retry.txt"

            @pytest.mark.vigil(retry=0)
            def test_no_retry():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "Should fail"
                assert True
        """)
        
        result = pytester.runpytest()
        
        # Should fail without retry
        assert result.ret == 1
        assert "Detected Flaky Tests" not in result.stdout.str()
