"""
Tests for resource limits via CLI parameters.
"""

pytest_plugins = ["pytester"]


class TestResourceLimitsCLI:
    """Test resource limits via CLI parameters."""

    def test_help_output_with_vigil_options(self, pytester):
        """Verify `pytest --help` renders Vigil options without crashing."""
        result = pytester.runpytest("--help")
        assert result.ret == 0
        output = result.stdout.str()
        assert "--vigil-cpu" in output
        assert "--vigil-stall-cpu-threshold" in output
    
    def test_cli_timeout_option(self, pytester):
        """Verify --vigil-timeout CLI option works."""
        pytester.makepyfile("""
            import time
            
            def test_cli_timeout():
                time.sleep(1.5)
        """)
        result = pytester.runpytest("--vigil-timeout=0.5")
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1

    def test_cli_timeout_passing(self, pytester):
        """Verify test passes under CLI timeout limit."""
        pytester.makepyfile("""
            import time
            
            def test_cli_timeout_pass():
                time.sleep(0.2)
                assert True
        """)
        result = pytester.runpytest("--vigil-timeout=1.0")
        assert result.ret == 0

    def test_cli_memory_option(self, pytester):
        """Verify --vigil-memory CLI option works."""
        pytester.makepyfile("""
            import time
            
            def test_cli_memory():
                data = ["x" * 1024 * 1024 for _ in range(30)]
                time.sleep(1)
        """)
        result = pytester.runpytest("--vigil-memory=10")
        full_output = result.stdout.str() + result.stderr.str()
        assert "Policy violation" in full_output
        assert result.ret == 1

    def test_cli_cpu_option(self, pytester):
        """Verify --vigil-cpu CLI option works."""
        pytester.makepyfile("""
            import time
            
            def test_cli_cpu():
                end = time.time() + 2
                while time.time() < end:
                    _ = [i*i for i in range(1000)]
        """)
        result = pytester.runpytest("--vigil-cpu=1")
        full_output = result.stdout.str() + result.stderr.str()
        assert "Policy violation" in full_output
        assert result.ret == 1

    def test_cli_combined_options(self, pytester):
        """Verify multiple CLI options work together."""
        pytester.makepyfile("""
            import time
            
            def test_cli_combined():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest("--vigil-timeout=1.0", "--vigil-memory=150", "--vigil-cpu=200")
        assert result.ret == 0

    def test_cli_timeout_with_violation(self, pytester):
        """Verify CLI timeout violation with combined options."""
        pytester.makepyfile("""
            import time
            
            def test_cli_timeout_violation():
                time.sleep(2)
        """)
        result = pytester.runpytest("--vigil-timeout=0.5", "--vigil-memory=150")
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1
