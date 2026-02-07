"""
Test stall detection behavior in CI environments.
- Verify that the CI multiplier is applied to stall timeouts when running in CI.
- Confirm that tests that would normally trigger stall violations pass due to the extended timeout in CI.
"""


pytest_plugins = ["pytester"]


class TestStallDetectionCI:
    """Test stall detection in CI environment."""
    
    def test_stall_detection_ci_multiplier(self, pytester, monkeypatch):
        """Verify CI multiplier applies to stall timeout."""
        monkeypatch.setenv("CI", "true")
        
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_ci_multiplier():
                # Sleep 1.5s. With CI multiplier (2x), timeout becomes 1.0s
                # So this should still trigger violation
                time.sleep(1.5)
        """)
        
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_detection_ci_extended_timeout(self, pytester, monkeypatch):
        """Verify CI multiplier extends timeout appropriately."""
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=1.0, stall_cpu_threshold=100.0)
            def test_ci_extended():
                # Sleep 1.8s. With CI multiplier (2x), timeout becomes 2.0s
                # So this should pass
                time.sleep(1.8)
                assert True
        """)
        
        result = pytester.runpytest()
        
        # Should pass due to CI multiplier
        assert result.ret == 0
    
    def test_stall_detection_no_ci(self, pytester, monkeypatch):
        """Verify stall detection without CI multiplier."""
        # Explicitly set CI to false
        monkeypatch.setenv("CI", "false")
        
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_no_ci():
                time.sleep(1.5)
        """)
        
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
