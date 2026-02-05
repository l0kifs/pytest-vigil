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
