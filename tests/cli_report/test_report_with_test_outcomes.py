"""
Test suite for verifying CLI report output with various test outcomes (passed, failed, skipped, xfail, xpass).
"""

pytest_plugins = ["pytester"]


class TestReportWithTestOutcomes:
    """Test CLI report with various test outcomes."""
    
    def test_report_with_passed_tests(self, pytester):
        """Verify passed tests appear in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.05)
                assert True
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        assert "Vigil Reliability Report" in output
        assert "test_pass" in output
        assert result.ret == 0
    
    def test_report_with_failed_tests(self, pytester):
        """Verify failed tests appear in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_fail():
                time.sleep(0.05)
                assert False
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        assert "Vigil Reliability Report" in output
        assert "test_fail" in output
        assert result.ret == 1
    
    def test_report_with_skipped_tests(self, pytester):
        """Verify skipped tests behavior in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.05)
                assert True
            
            @pytest.mark.skip(reason="test skip")
            def test_skip():
                pass
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        # Skipped tests don't have vigil monitoring, so shouldn't appear in report
        assert "test_pass" in output
        # test_skip should not be in vigil report (no vigil marker)
        assert result.ret == 0
    
    def test_report_with_xfail_tests(self, pytester):
        """Verify xfail tests behavior in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.05)
                assert True
            
            @pytest.mark.xfail(reason="expected to fail")
            @pytest.mark.vigil(timeout=2.0)
            def test_xfail():
                time.sleep(0.05)
                assert False
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        assert "Vigil Reliability Report" in output
        assert "test_pass" in output
        # xfail tests with vigil marker should appear in report
        assert "test_xfail" in output
        assert result.ret == 0
    
    def test_report_with_xpass_tests(self, pytester):
        """Verify xpass tests appear in report."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.05)
                assert True
            
            @pytest.mark.xfail(reason="expected to fail", strict=False)
            @pytest.mark.vigil(timeout=2.0)
            def test_xpass():
                time.sleep(0.05)
                assert True
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        assert "Vigil Reliability Report" in output
        assert "test_xpass" in output
        assert result.ret == 0
    
    def test_report_with_mixed_outcomes(self, pytester):
        """Verify report shows all test types correctly."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_pass():
                time.sleep(0.05)
                assert True
            
            @pytest.mark.vigil(timeout=2.0)
            def test_fail():
                time.sleep(0.05)
                assert False
            
            @pytest.mark.skip(reason="skipped")
            def test_skip():
                pass
            
            @pytest.mark.xfail
            @pytest.mark.vigil(timeout=2.0)
            def test_xfail():
                assert False
        """)
        
        result = pytester.runpytest("--vigil-cli-report-verbosity=full")
        output = result.stdout.str()
        
        assert "Vigil Reliability Report" in output
        # All vigil-monitored tests should appear
        assert "test_pass" in output
        assert "test_fail" in output
        assert "test_xfail" in output
        assert result.ret == 1
