"""
Tests for retry mechanism behavior in CI environment, ensuring retry count is not multiplied while timeouts are.
"""

pytest_plugins = ["pytester"]


class TestRetryCIEnvironment:
    """Test retry behavior in CI environment."""
    
    def test_retry_count_not_multiplied_in_ci(self, pytester, monkeypatch):
        """Verify retry count is NOT multiplied in CI (unlike timeouts)."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "ci_retry.txt"

            @pytest.mark.vigil(timeout=1.0, retry=1)
            def test_ci_retry():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        
        # Set CI environment
        monkeypatch.setenv("CI", "true")
        result = pytester.runpytest()
        
        # Should pass with retry=1 (not multiplied by ci_multiplier=2.0)
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
    
    def test_retry_with_ci_and_timeout_multiplier(self, pytester, monkeypatch):
        """Verify retry works alongside CI timeout multiplier."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "ci_timeout_retry.txt"

            @pytest.mark.vigil(timeout=1.0, retry=2)
            def test_ci_timeout_retry():
                time.sleep(0.5)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        
        monkeypatch.setenv("CI", "true")
        result = pytester.runpytest()
        
        # Timeout should be multiplied to 2.0s, retry should work
        assert result.ret == 0
