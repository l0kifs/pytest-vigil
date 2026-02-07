"""
Test that the retry mechanism does not interfere with other features of the plugin, 
such as session timeouts or other test markers. 
This ensures that retry logic is isolated and does not cause unintended side effects on unrelated tests or features.
"""

pytest_plugins = ["pytester"]


class TestRetryNonInterference:
    """Test that retry doesn't interfere with other features."""
    
    def test_retry_with_session_timeout(self, pytester):
        """Verify retry works alongside session timeout."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "session_retry.txt"

            @pytest.mark.vigil(retry=2)
            def test_with_session_timeout():
                time.sleep(0.1)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                assert True
        """)
        
        result = pytester.runpytest("--vigil-session-timeout=10")
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
    
    def test_retry_doesnt_affect_other_tests(self, pytester):
        """Verify retry on one test doesn't affect others."""
        pytester.makepyfile("""
            import pytest
            import os

            @pytest.mark.vigil(retry=2)
            def test_with_retry():
                fname = "with_retry.txt"
                if not os.path.exists(fname):
                    with open(fname, "w") as f:
                        f.write("1")
                    assert False
                assert True

            @pytest.mark.vigil(timeout=2.0)
            def test_without_retry():
                # This should fail immediately
                assert False, "No retry"
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        
        # One test should pass (with retry), one should fail (no retry)
        assert result.ret == 1
        
        output = result.stdout.str()
        assert "test_with_retry" in output
        assert "test_without_retry" in output
        
        # Check the flaky tests list specifically
        assert "Detected Flaky Tests (Passed on Retry):" in output
        # Extract the flaky tests section - between the header and the table
        flaky_start = output.find("Detected Flaky Tests (Passed on Retry):")
        table_start = output.find("Test ID", flaky_start)
        flaky_list_section = output[flaky_start:table_start]
        
        # Only test_with_retry should be in the flaky list
        assert "test_with_retry" in flaky_list_section
        assert "test_without_retry" not in flaky_list_section
