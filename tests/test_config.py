import pytest
import os

pytest_plugins = ["pytester"]

def test_config_env_var_timeout(pytester, monkeypatch):
    """Verify that PYTEST_VIGIL__TIMEOUT environment variable sets the default timeout."""
    monkeypatch.setenv("PYTEST_VIGIL__TIMEOUT", "0.5")
    
    pytester.makepyfile("""
        import time
        import pytest
        
        def test_sleep_env_timeout():
            time.sleep(1.0)
    """)
    
    # limits are applied via the plugin, which reads env vars
    result = pytester.runpytest()
    
    result.stdout.fnmatch_lines([
        "*Test timed out (Vigil)*"
    ])
    assert result.ret == 1

def test_config_cli_overrides_env(pytester, monkeypatch):
    """Verify that CLI options override environment variables."""
    monkeypatch.setenv("PYTEST_VIGIL__TIMEOUT", "2.0")
    
    pytester.makepyfile("""
        import time
        import pytest
        
        def test_sleep_cli_override():
            time.sleep(1.0)
    """)
    
    # CLI sets 0.5, which is stricter than ENV 2.0. Test sleeps 1.0, so it should fail.
    result = pytester.runpytest("--vigil-timeout=0.5")
    
    result.stdout.fnmatch_lines([
        "*Test timed out (Vigil)*"
    ])
    assert result.ret == 1

def test_config_marker_overrides_all(pytester, monkeypatch):
    """Verify that Markers override both CLI and environment variables."""
    monkeypatch.setenv("PYTEST_VIGIL__TIMEOUT", "2.0")
    
    pytester.makepyfile("""
        import time
        import pytest
        
        @pytest.mark.vigil(timeout=0.5)
        def test_sleep_marker_override():
            time.sleep(1.0)
    """)
    
    # CLI sets 1.5, ENV sets 2.0. Marker sets 0.5. Test sleeps 1.0. Should fail.
    result = pytester.runpytest("--vigil-timeout=1.5")
    
    result.stdout.fnmatch_lines([
        "*Test timed out (Vigil)*"
    ])
    assert result.ret == 1

def test_config_cli_stall_timeout(pytester):
    """Verify that --vigil-stall-timeout CLI option works."""
    pytester.makepyfile("""
        import time
        
        def test_stall_via_cli():
            # Sleep for 1.5 seconds with low CPU
            time.sleep(1.5)
    """)
    
    # Set stall timeout to 0.5s via CLI, should trigger
    result = pytester.runpytest("--vigil-stall-timeout=0.5", "--vigil-stall-cpu-threshold=100")
    
    result.stdout.fnmatch_lines([
        "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
    ])
    assert result.ret == 1

def test_config_cli_stall_cpu_threshold(pytester):
    """Verify that --vigil-stall-cpu-threshold CLI option works."""
    pytester.makepyfile("""
        import time
        
        def test_stall_threshold_via_cli():
            # Sleep with very low CPU usage
            time.sleep(1.5)
    """)
    
    # Set stall timeout and high threshold via CLI
    result = pytester.runpytest("--vigil-stall-timeout=0.5", "--vigil-stall-cpu-threshold=100")
    
    result.stdout.fnmatch_lines([
        "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
    ])
    assert result.ret == 1

def test_config_stall_cli_overrides_env(pytester, monkeypatch):
    """Verify that CLI stall options override environment variables."""
    monkeypatch.setenv("PYTEST_VIGIL__STALL_TIMEOUT", "5.0")
    monkeypatch.setenv("PYTEST_VIGIL__STALL_CPU_THRESHOLD", "0.1")
    
    pytester.makepyfile("""
        import time
        
        def test_stall_cli_override():
            time.sleep(1.5)
    """)
    
    # CLI sets stricter stall_timeout=0.5, should trigger even though ENV has 5.0
    result = pytester.runpytest("--vigil-stall-timeout=0.5", "--vigil-stall-cpu-threshold=100")
    
    result.stdout.fnmatch_lines([
        "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
    ])
    assert result.ret == 1

def test_config_stall_marker_overrides_cli(pytester):
    """Verify that Marker stall options override CLI."""
    pytester.makepyfile("""
        import time
        import pytest
        
        @pytest.mark.vigil(stall_timeout=0.5, stall_cpu_threshold=100.0)
        def test_stall_marker_override():
            time.sleep(1.5)
    """)
    
    # CLI sets lenient timeout=5.0, but marker sets strict 0.5
    result = pytester.runpytest("--vigil-stall-timeout=5.0", "--vigil-stall-cpu-threshold=0.1")
    
    result.stdout.fnmatch_lines([
        "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
    ])
    assert result.ret == 1

def test_config_env_var_stall_timeout(pytester, monkeypatch):
    """Verify that PYTEST_VIGIL__STALL_TIMEOUT environment variable works."""
    monkeypatch.setenv("PYTEST_VIGIL__STALL_TIMEOUT", "0.5")
    monkeypatch.setenv("PYTEST_VIGIL__STALL_CPU_THRESHOLD", "100.0")
    
    pytester.makepyfile("""
        import time
        
        def test_stall_env_timeout():
            time.sleep(1.5)
    """)
    
    result = pytester.runpytest()
    
    result.stdout.fnmatch_lines([
        "*Policy violation: *limit_type=<InteractionType.STALL: 'stall'>*"
    ])
    assert result.ret == 1
