"""
Test stall detection behavior with different test outcomes in pytest-vigil.
- Verify that stall detection runs on passing, failing, skipped, xfail, and xpass tests.
- Confirm that stall detection violations are reported correctly for passing and failing tests.
- Ensure that skipped tests do not trigger stall detection.
- Check that xfail tests are marked as xfailed regardless of stall detection.
- Verify that xpass tests are handled correctly when stall detection is enabled.
"""

pytest_plugins = ["pytester"]


class TestStallDetectionWithOutcomes:
    """Test stall detection with different test outcomes."""
    
    def test_stall_detection_with_passing_test(self, pytester):
        """Verify stall detection violation on a passing test."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_pass_but_stalled():
                time.sleep(1.5)
                assert True  # Test would pass, but stalls
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_with_failing_test(self, pytester):
        """Verify stall detection violation on a failing test."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_fail_and_stalled():
                time.sleep(1.5)
                assert False  # Test fails AND stalls
        """)
        result = pytester.runpytest()
        
        # Should show violation (stall detected before assertion)
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_with_skipped_test(self, pytester):
        """Verify stall detection doesn't apply to skipped tests."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            @pytest.mark.skip(reason="Skipped test")
            def test_skip_with_stall():
                time.sleep(1.5)  # Would stall, but test is skipped
        """)
        result = pytester.runpytest()
        
        # Skipped tests shouldn't trigger monitoring
        result.stdout.fnmatch_lines(["*1 skipped*"])
        assert result.ret == 0
    
    def test_stall_detection_with_xfail_test(self, pytester):
        """Verify stall detection runs on xfail marked test (but test still marked xfail)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            @pytest.mark.xfail(reason="Expected to fail")
            def test_xfail_with_stall():
                time.sleep(1.5)
                assert False
        """)
        result = pytester.runpytest()
        
        # xfail tests are marked xfailed regardless of stall detection
        result.stdout.fnmatch_lines(["*1 xfailed*"])
        # Exit code 0 for xfail
        assert result.ret == 0
    
    def test_stall_detection_with_xpass_test(self, pytester):
        """Verify stall detection runs on xpass (unexpectedly passing) test."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=2.0, stall_cpu_threshold=100.0)
            @pytest.mark.xfail(reason="Expected to fail")
            def test_xpass_with_stall():
                time.sleep(0.1)
                assert True  # Unexpectedly passes, no stall
        """)
        result = pytester.runpytest()
        
        # xpass tests show as XPASS (X capital) in output
        result.stdout.fnmatch_lines(["*1 xpassed*"])
        # Exit code 0 for xpass with default strict_xfail=False
        assert result.ret == 0
