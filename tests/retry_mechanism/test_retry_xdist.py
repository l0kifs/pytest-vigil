"""
Tests for retry mechanism with pytest-xdist.
"""

pytest_plugins = ["pytester"]


class TestRetryXDist:
    """Test retry mechanism with pytest-xdist."""
    
    def test_retry_mechanism_xdist(self, pytester):
        """Verify that retry mechanism works correctly in xdist mode."""
        pytester.makepyfile("""
            import pytest
            import os
            
            FILENAME = "flaky_xdist.txt"

            @pytest.mark.vigil(retry=2)
            def test_flaky_xdist():
                if not os.path.exists(FILENAME):
                    with open(FILENAME, "w") as f:
                        f.write("1")
                    assert False, "First run fails"
                else:
                    assert True
        """)
        
        result = pytester.runpytest("-n", "2")
        
        assert result.ret == 0
    
    def test_retry_xdist_multiple_workers(self, pytester):
        """Verify retry works with multiple workers."""
        pytester.makepyfile("""
            import pytest
            import os

            @pytest.mark.vigil(retry=2)
            def test_flaky_1():
                fname = "flaky_1.txt"
                if not os.path.exists(fname):
                    with open(fname, "w") as f:
                        f.write("1")
                    assert False
                assert True

            @pytest.mark.vigil(retry=2)
            def test_flaky_2():
                fname = "flaky_2.txt"
                if not os.path.exists(fname):
                    with open(fname, "w") as f:
                        f.write("1")
                    assert False
                assert True
        """)
        
        result = pytester.runpytest("-n", "4")
        assert result.ret == 0
