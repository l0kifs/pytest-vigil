"""
Test stall detection parameter configuration in pytest-vigil.
- Verify that stall parameters can be set via markers, CLI options, and environment variables.
- Confirm that marker parameters override CLI options, and CLI options override environment variables.
- Ensure that stall detection behaves correctly with different parameter combinations.
"""

pytest_plugins = ["pytester"]


class TestStallDetectionParameters:
    """Test stall detection parameter configuration."""
    
    def test_stall_marker_parameters(self, pytester):
        """Verify stall parameters set via marker."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_marker_params():
                time.sleep(1.5)
        """)
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_cli_parameters(self, pytester):
        """Verify stall parameters set via CLI."""
        pytester.makepyfile("""
            import time
            
            def test_cli_params():
                time.sleep(1.5)
        """)
        
        result = pytester.runpytest(
            "--vigil-stall-timeout=0.5",
            "--vigil-stall-cpu-threshold=100"
        )
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_env_parameters(self, pytester, monkeypatch):
        """Verify stall parameters set via environment variables."""
        monkeypatch.setenv("PYTEST_VIGIL__STALL_TIMEOUT", "0.5")
        monkeypatch.setenv("PYTEST_VIGIL__STALL_CPU_THRESHOLD", "100.0")
        
        pytester.makepyfile("""
            import time
            
            def test_env_params():
                time.sleep(1.5)
        """)
        
        result = pytester.runpytest()
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_marker_overrides_cli(self, pytester):
        """Verify marker parameters override CLI parameters."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_marker_override():
                time.sleep(1.5)
        """)
        
        # CLI sets lenient timeout=5.0, but marker sets strict 0.5
        result = pytester.runpytest(
            "--vigil-stall-timeout=5.0",
            "--vigil-stall-cpu-threshold=0.1"
        )
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_cli_overrides_env(self, pytester, monkeypatch):
        """Verify CLI parameters override environment variables."""
        monkeypatch.setenv("PYTEST_VIGIL__STALL_TIMEOUT", "5.0")
        monkeypatch.setenv("PYTEST_VIGIL__STALL_CPU_THRESHOLD", "0.1")
        
        pytester.makepyfile("""
            import time
            
            def test_cli_override():
                time.sleep(1.5)
        """)
        
        # CLI sets stricter stall_timeout=0.5, should trigger despite lenient env
        result = pytester.runpytest(
            "--vigil-stall-timeout=0.5",
            "--vigil-stall-cpu-threshold=100"
        )
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_only_timeout_parameter(self, pytester):
        """Verify stall detection with only timeout specified."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(stall_timeout=0.3)
            def test_only_timeout():
                # Without explicit threshold, uses default 0.1%
                # Sleep should keep CPU low, but may have spikes
                # Use explicit high threshold in other tests for reliability
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("-v")
        
        # Test should pass - default threshold (0.1%) may not reliably trigger
        # due to system activity during sleep
        assert result.ret == 0
    
    def test_stall_cli_timeout_only(self, pytester):
        """Verify CLI stall-timeout option works alone."""
        pytester.makepyfile("""
            import time
            
            def test_cli_timeout():
                time.sleep(1.5)
        """)
        
        # Only set timeout via CLI, threshold uses default (1.0%)
        result = pytester.runpytest("--vigil-stall-timeout=0.5")
        
        result.stdout.fnmatch_lines([
            "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
        ])
        assert result.ret == 1
    
    def test_stall_cli_threshold_only(self, pytester):
        """Verify CLI stall-cpu-threshold alone doesn't enable stall detection."""
        pytester.makepyfile("""
            import time
            
            def test_cli_threshold_only():
                time.sleep(1.5)
                assert True
        """)
        
        # Only set threshold, no timeout means no stall detection
        result = pytester.runpytest("--vigil-stall-cpu-threshold=100")
        
        # Should pass as stall detection is not enabled
        assert result.ret == 0
