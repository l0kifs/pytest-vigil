"""
Tests for configuration precedence of resource limits.
"""

pytest_plugins = ["pytester"]


class TestResourceLimitsPrecedence:
    """Test configuration precedence: marker > CLI > env."""
    
    def test_marker_overrides_cli(self, pytester):
        """Verify marker takes precedence over CLI."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_marker_override():
                time.sleep(0.5)
        """)
        result = pytester.runpytest("--vigil-timeout=0.1")
        assert result.ret == 0  # Marker timeout=2.0 allows it to pass

    def test_marker_overrides_env(self, pytester, monkeypatch):
        """Verify marker takes precedence over environment variable."""
        monkeypatch.setenv("PYTEST_VIGIL__TIMEOUT", "0.1")
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_marker_over_env():
                time.sleep(0.5)
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_cli_overrides_env(self, pytester, monkeypatch):
        """Verify CLI takes precedence over environment variable."""
        monkeypatch.setenv("PYTEST_VIGIL__TIMEOUT", "2.0")
        pytester.makepyfile("""
            import time
            
            def test_cli_over_env():
                time.sleep(1.0)
        """)
        result = pytester.runpytest("--vigil-timeout=0.5")
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1

    def test_env_var_default(self, pytester, monkeypatch):
        """Verify environment variable is used when no CLI or marker."""
        monkeypatch.setenv("PYTEST_VIGIL__TIMEOUT", "0.5")
        pytester.makepyfile("""
            import time
            
            def test_env_default():
                time.sleep(1.0)
        """)
        result = pytester.runpytest()
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1

    def test_function_marker_overrides_class(self, pytester):
        """Verify function marker overrides class marker."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.1)
            class TestClass:
                @pytest.mark.vigil(timeout=5)
                def test_override_extended(self):
                    time.sleep(0.5)
                
                def test_inherit_class(self):
                    time.sleep(0.5)
        """)
        result = pytester.runpytest("-v")
        result.stdout.fnmatch_lines([
            "*test_override_extended PASSED*",
            "*test_inherit_class FAILED*"
        ])
        assert result.ret == 1

    def test_partial_marker_override(self, pytester):
        """Verify partial marker override (timeout from marker, memory from CLI)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_partial():
                time.sleep(0.2)
                data = ["x" * 1024 for _ in range(10)]
                assert True
        """)
        result = pytester.runpytest("--vigil-memory=200")
        assert result.ret == 0
