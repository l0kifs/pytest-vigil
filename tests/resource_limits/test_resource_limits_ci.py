"""
Test resource limits in CI environment.
"""

import pytest

pytest_plugins = ["pytester"]


class TestResourceLimitsCI:
    """Test CI multiplier application for resource limits."""
    
    def test_ci_multiplier_timeout(self, pytester):
        """Verify CI multiplier is applied to timeout."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_ci_timeout():
                time.sleep(0.8)  # Would fail without multiplier
        """)
        with pytest.MonkeyPatch.context() as m:
            m.setenv("CI", "true")
            result = pytester.runpytest()
            assert result.ret == 0  # Passes with 2x multiplier (timeout=1.0)

    def test_no_ci_multiplier(self, pytester):
        """Verify no multiplier when CI is not set."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_no_ci():
                time.sleep(0.8)
        """)
        with pytest.MonkeyPatch.context() as m:
            m.setenv("CI", "false")
            result = pytester.runpytest()
            result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
            assert result.ret == 1

    def test_github_actions_detection(self, pytester):
        """Verify GITHUB_ACTIONS environment variable triggers CI multiplier."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.5)
            def test_github_actions():
                time.sleep(0.8)
        """)
        with pytest.MonkeyPatch.context() as m:
            m.setenv("GITHUB_ACTIONS", "true")
            result = pytester.runpytest()
            assert result.ret == 0

    def test_ci_multiplier_memory(self, pytester):
        """Verify CI multiplier concept with memory (no direct multiplier but test compatibility)."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=150)
            def test_ci_memory():
                data = ["x" * 1024 * 10 for _ in range(100)]  # ~1MB
                time.sleep(0.2)
                assert True
        """)
        with pytest.MonkeyPatch.context() as m:
            m.setenv("CI", "true")
            result = pytester.runpytest()
            assert result.ret == 0

    def test_ci_multiplier_cpu(self, pytester):
        """Verify CI multiplier with CPU limits."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(cpu=200)
            def test_ci_cpu():
                time.sleep(0.2)
                result = sum(range(1000))
                assert result > 0
        """)
        with pytest.MonkeyPatch.context() as m:
            m.setenv("CI", "true")
            result = pytester.runpytest()
            assert result.ret == 0
