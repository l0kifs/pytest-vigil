import pytest

pytest_plugins = ["pytester"]

def test_timeout_fixture(pytester):
    """Verify that the timeout fixture works."""
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(timeout=0.5)
        def test_sleep():
            time.sleep(1)
    """)
    result = pytester.runpytest()
    # Check that we see the exception in the output
    result.stdout.fnmatch_lines([
        "*Test timed out (Vigil)*"
    ])
    assert result.ret == 1

def test_slow_fixture_timeout(pytester):
    """Verify that a slow fixture setup triggers the timeout."""
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.fixture
        def slow_setup():
            time.sleep(2)
            return True

        @pytest.mark.vigil(timeout=1)
        def test_with_slow_fixture(slow_setup):
            pass
    """)
    result = pytester.runpytest()
    stdout_str = result.stdout.str()
    stderr_str = result.stderr.str()
    full_output = stdout_str + stderr_str
    
    assert "TimeoutException: Test timed out (Vigil)" in full_output
    assert result.ret == 1

def test_exception_swallowing_attempt(pytester):
    """Verify that catching Exception does not catch the configured signal/TimeoutException."""
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(timeout=1)
        def test_swallow():
            try:
                time.sleep(2)
            except Exception:
                pass 
    """)
    result = pytester.runpytest()
    stdout = result.stdout.str()
    # Should still fail
    assert "TimeoutException: Test timed out (Vigil)" in stdout + result.stderr.str()
    assert result.ret == 1

def test_zero_limit_is_immediate(pytester):
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(timeout=0)
        def test_zero():
            time.sleep(1)
    """)
    result = pytester.runpytest()
    stdout_str = result.stdout.str()
    stderr_str = result.stderr.str()
    full_output = stdout_str + stderr_str

    assert "TimeoutException: Test timed out (Vigil)" in full_output
    assert "Policy violation" in full_output

    assert result.ret == 1

def test_memory_limit_fixture(pytester):
    """Verify that the memory limit works."""
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(memory=10)
        def test_memory():
            # Allocate ~20MB
            data = ["x" * 1024 * 1024 for _ in range(20)]
            time.sleep(1) # Allow monitor to catch it
    """)
    result = pytester.runpytest()
    stdout_str = result.stdout.str()
    stderr_str = result.stderr.str()
    full_output = stdout_str + stderr_str
    
    assert "TimeoutException: Test timed out (Vigil)" in full_output
    assert "Policy violation" in full_output

    assert result.ret == 1

def test_cpu_limit_fixture(pytester):
    """Verify that the CPU limit works."""
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(cpu=1) 
        # 1% is very low, should trigger for any compute intensive task
        def test_cpu():
            end = time.time() + 2
            while time.time() < end:
                _ = [i*i for i in range(1000)]
    """)
    result = pytester.runpytest()
    stdout_str = result.stdout.str()
    stderr_str = result.stderr.str()
    full_output = stdout_str + stderr_str
    
    assert "TimeoutException: Test timed out (Vigil)" in full_output
    assert "Policy violation" in full_output

    assert result.ret == 1
