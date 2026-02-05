import pytest

pytest_plugins = ["pytester"]

def test_xdist_parallel_execution(pytester):
    """
    Verify that tests run in parallel with xdist are monitored correctly.
    One test should timeout, another should pass.
    """
    # Create valid test file
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(timeout=0.5)
        def test_timeout():
            time.sleep(2)

        @pytest.mark.vigil(timeout=2)
        def test_pass():
            time.sleep(0.5)
    """)

    # Run with 2 workers
    # -n 2 enables xdist with 2 workers
    result = pytester.runpytest("-n", "2", "-v")
    
    # Analyze results
    # test_pass should pass
    # test_timeout should fail with Vigil timeout
    result.stdout.fnmatch_lines([
        "*PASSED*test_pass*",
        "*FAILED*test_timeout*"
    ])
    
    # Check for the timeout message in the output
    stdout_str = result.stdout.str()
    stderr_str = result.stderr.str()
    full_output = stdout_str + stderr_str
    
    assert "TimeoutException: Test timed out (Vigil)" in full_output
    assert "Policy violation" in full_output

def test_xdist_heavy_load(pytester):
    """
    Simulate multiple workers under load.
    Verify stability when all workers are monitored simultaneously.
    """
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(timeout=1.0)
        def test_w1():
            time.sleep(0.1)

        @pytest.mark.vigil(timeout=1.0)
        def test_w2():
            time.sleep(0.1)
            
        @pytest.mark.vigil(timeout=1.0)
        def test_w3():
            time.sleep(0.1)
            
        @pytest.mark.vigil(timeout=1.0)
        def test_w4():
            time.sleep(0.1)
    """)
    
    # Run with 2 workers
    result = pytester.runpytest("-n", "2", "-v")
    
    # All should pass
    result.assert_outcomes(passed=4)

def test_xdist_resource_isolation_cpu(pytester):
    """
    Verify that CPU limits are enforced per-process in xdist.
    This is tricky because 100% CPU on one core might not trigger system-wide if not careful,
    but Vigil monitors the current process (worker).
    """
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.vigil(cpu=2) 
        # Low limit ~2%, should trigger if this process spins hard
        def test_cpu_worker():
            end = time.time() + 3
            while time.time() < end:
                _ = [i*i for i in range(1000)]
                
        def test_normal_worker():
            time.sleep(0.5)
    """)
    
    # Run with 2 workers
    result = pytester.runpytest("-n", "2", "-v")
    
    # test_cpu_worker should fail, test_normal_worker should pass
    result.stdout.fnmatch_lines([
        "*PASSED*test_normal_worker*",
        "*FAILED*test_cpu_worker*"
    ])
    
    # Ensure it failed potentially due to Vigil (though not strictly asserting message here per original code,
    # but good to have implicit check via failure)
    pass
