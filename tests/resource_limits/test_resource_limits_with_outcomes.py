"""
Comprehensive tests for resource limits functionality with different test outcomes.
"""

pytest_plugins = ["pytester"]


class TestResourceLimitsWithOutcomes:
    """Test resource limits with all pytest test outcomes."""
    
    def test_passed_test_with_timeout(self, pytester):
        """Verify passed test with timeout limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_pass():
                time.sleep(0.1)
                assert 1 + 1 == 2
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_pass PASSED*"])
        assert result.ret == 0

    def test_failed_test_with_timeout(self, pytester):
        """Verify failed test (assertion) with timeout limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_fail():
                time.sleep(0.1)
                assert 1 + 1 == 3
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_fail FAILED*"])
        result.stdout.fnmatch_lines(["*AssertionError*"])
        assert result.ret == 1

    def test_skipped_test_with_timeout(self, pytester):
        """Verify skipped test with timeout limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            @pytest.mark.skip(reason="Testing skip")
            def test_skip():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_skip SKIPPED*"])
        assert result.ret == 0

    def test_xfail_test_with_timeout(self, pytester):
        """Verify xfail test with timeout limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            @pytest.mark.xfail(reason="Expected failure")
            def test_xfail():
                time.sleep(0.1)
                assert False
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_xfail*"])
        assert result.ret == 0

    def test_xpass_test_with_timeout(self, pytester):
        """Verify xpass test with timeout limit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            @pytest.mark.xfail(reason="Expected failure")
            def test_xpass():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines(["*test_xpass*"])
        assert result.ret == 0

    def test_mixed_outcomes(self, pytester):
        """Verify multiple tests with different outcomes and resource limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_pass():
                time.sleep(0.1)
                assert True

            @pytest.mark.vigil(timeout=1.0)
            def test_fail():
                time.sleep(0.1)
                assert False

            @pytest.mark.vigil(timeout=1.0)
            @pytest.mark.skip(reason="Skip")
            def test_skip():
                pass
        """)
        result = pytester.runpytest("-v")
        assert result.ret == 1  # Has failed test
