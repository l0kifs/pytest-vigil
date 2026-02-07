"""
Test interactions between resource limits and other pytest-vigil features, such as timeouts and stall detection.
"""

pytest_plugins = ["pytester"]


class TestResourceLimitsInteractions:
    """Test resource limits interaction with other pytest-vigil features."""
    
    def test_timeout_with_stall_detection(self, pytester):
        """Verify timeout and stall detection work together."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0, stall_timeout=0.5, stall_cpu_threshold=100.0)
            def test_timeout_stall():
                time.sleep(1.5)  # Stall should trigger first
        """)
        result = pytester.runpytest()
        full_output = result.stdout.str() + result.stderr.str()
        assert "Policy violation" in full_output
        assert result.ret == 1
