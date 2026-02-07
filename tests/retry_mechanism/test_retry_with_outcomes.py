"""
Test retry mechanism with various pytest test outcomes (pass, fail, skip, xfail, xpass).
- Verify that retry works correctly with each outcome type.
- Ensure that skipped, xfail, and xpass tests are not retried.
- Check that flaky test detection only occurs for tests that eventually pass after retries.
"""

pytest_plugins = ["pytester"]


class TestRetryWithOutcomes:
    """Test retry with all pytest test outcomes."""
    
    def test_retry_with_failing_test(self, pytester):
        """Verify retry with test that eventually passes."""
        pytester.makepyfile("""
            import pytest
            import os

            FILENAME = "fail_pass.txt"

            @pytest.mark.vigil(retry=2)
            def test_fail_then_pass():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First attempt fails"
                else:
                    assert True
        """)
        
        result = pytester.runpytest()
        assert result.ret == 0
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
    
    def test_retry_with_passing_test(self, pytester):
        """Verify passing test with retry doesn't retry."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(retry=2)
            def test_always_pass():
                assert True
        """)
        
        result = pytester.runpytest()
        assert result.ret == 0
        # Should NOT show flaky test message (didn't need retry)
        assert "Detected Flaky Tests" not in result.stdout.str()
    
    def test_retry_with_skipped_test(self, pytester):
        """Verify skipped test is not retried."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(retry=2)
            @pytest.mark.skip(reason="Testing skip")
            def test_skip():
                assert False, "Should never run"
        """)
        
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_skip SKIPPED*"])
        assert result.ret == 0
        # Skipped tests should not be retried
        assert "Detected Flaky Tests" not in result.stdout.str()
    
    def test_retry_with_xfail_test(self, pytester):
        """Verify xfail test is not retried."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(retry=2)
            @pytest.mark.xfail(reason="Expected failure")
            def test_xfail():
                assert False
        """)
        
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_xfail*"])
        assert result.ret == 0
        # xfail tests should not be retried
        assert "Detected Flaky Tests" not in result.stdout.str()
    
    def test_retry_with_xpass_test(self, pytester):
        """Verify xpass test is not retried."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.vigil(retry=2)
            @pytest.mark.xfail(reason="Expected failure but passes")
            def test_xpass():
                assert True
        """)
        
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_xpass*"])
        assert result.ret == 0
        # xpass tests should not be retried
        assert "Detected Flaky Tests" not in result.stdout.str()
