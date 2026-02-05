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
    # Pytest prints "Captured stderr call" to stdout on failure
    result.stdout.fnmatch_lines([
        "*Test timed out (Vigil)*"
    ])
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
    # Loguru writes to stderr, which pytest captures and prints to stdout on failure
    # The output contains the exception, and usually log output.
    # We'll check for the generic interruption triggers which implies the monitor fired.
    # Logic: If the test finished successfully (no exception), it would be a failure.
    # If it failed with TimeoutException, it means Vigil worked.
    # We verify it's NOT a standard python TimeoutError or crash.
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
    # Check full output for the log message, ignoring where exactly it ended up
    stdout_str = result.stdout.str()
    stderr_str = result.stderr.str()
    full_output = stdout_str + stderr_str
    
    assert "TimeoutException: Test timed out (Vigil)" in full_output
    assert "Policy violation" in full_output

    assert result.ret == 1

def test_marker_overrides_cli(pytester):
    """Verify marker takes precedence over CLI."""
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(timeout=2)
        def test_pass_with_override():
            time.sleep(0.5)
    """)
    result = pytester.runpytest("--vigil-timeout=0.1")
    assert result.ret == 0

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
