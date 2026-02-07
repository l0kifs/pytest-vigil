"""
Tests for retry mechanism with limits. 
Ensures that retry count is respected and does not exceed specified limits.
"""

pytest_plugins = ["pytester"]


class TestRetryWithLimits:
    """Test retry mechanism with resource limits."""
    
    def test_retry_with_timeout(self, pytester):
        """Verify retry mechanism works with timeout."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "retry_timeout.txt"

            @pytest.mark.vigil(timeout=2.0, retry=2)
            def test_retry_timeout():
                time.sleep(0.1)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First run fails"
                else:
                    assert True
        """)
        result = pytester.runpytest()
        result.stdout.fnmatch_lines(["*Detected Flaky Tests*"])
        assert result.ret == 0

    def test_retry_with_memory(self, pytester):
        """Verify retry mechanism works with memory limits."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "retry_memory.txt"

            @pytest.mark.vigil(memory=200, retry=2)
            def test_retry_memory():
                data = ["x" * 1024 for _ in range(10)]
                time.sleep(0.1)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_retry_with_cpu(self, pytester):
        """Verify retry mechanism works with CPU limits."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "retry_cpu.txt"

            @pytest.mark.vigil(cpu=200, retry=2)
            def test_retry_cpu():
                time.sleep(0.1)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
    
    def test_retry_with_stall_detection(self, pytester):
        """Verify retry works with stall detection."""
        pytester.makepyfile("""
            import pytest
            import os
            import time

            FILENAME = "retry_stall.txt"

            @pytest.mark.vigil(stall_timeout=2.0, retry=2)
            def test_retry_stall():
                time.sleep(0.1)
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False
                else:
                    assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0
