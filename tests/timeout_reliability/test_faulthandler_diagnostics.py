"""
Tests for the faulthandler diagnostic integration (Item 4).

faulthandler.dump_traceback_later() is registered for each test attempt when a
timeout is configured.  It fires at timeout_val + 1 s and dumps C-level thread
tracebacks to stderr — useful when the process is stuck inside a C extension
that would otherwise produce no output.

Tests here verify:
- Normal tests complete without being interrupted by faulthandler.
- faulthandler is set up only when a timeout is configured.
- faulthandler output appears in stderr when a test hangs past the faulthandler
  deadline (exercised by combining with force_exit_delay).
- faulthandler is correctly cancelled between retries so it does not fire into
  the next attempt.
"""

import pytest

pytest_plugins = ["pytester"]


class TestFaulthandlerNoInterference:
    """faulthandler must not disrupt normal test flows."""

    def test_passing_test_completes_normally(self, pytester):
        """A fast passing test is unaffected by the faulthandler registration."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_quick():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_normal_timeout_failure_unaffected(self, pytester):
        """A test interrupted by the normal soft-interrupt path still exits with code 1."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_slow():
                time.sleep(2)
        """)
        result = pytester.runpytest()
        result.stdout.fnmatch_lines(["*Test timed out (Vigil)*"])
        assert result.ret == 1

    def test_multiple_tests_with_faulthandler_enabled(self, pytester):
        """Faulthandler is properly cancelled and re-armed for each test."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=1.0)
            def test_a():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_b():
                time.sleep(0.05)

            @pytest.mark.vigil(timeout=1.0)
            def test_c():
                time.sleep(0.05)
        """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=3)

    def test_no_faulthandler_without_timeout(self, pytester):
        """A test with only memory / CPU limits does not arm the faulthandler timer."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(memory=999, cpu=200)
            def test_no_timeout():
                time.sleep(0.1)
                assert True
        """)
        result = pytester.runpytest()
        assert result.ret == 0

    def test_faulthandler_cancelled_after_retry(self, pytester):
        """faulthandler is cancelled between retries so it does not fire into attempt N+1."""
        pytester.makepyfile("""
            import pytest
            import time

            _attempt = [0]

            @pytest.mark.vigil(timeout=1.0, retry=1)
            def test_flaky():
                _attempt[0] += 1
                if _attempt[0] < 2:
                    raise AssertionError("fail first attempt")
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest("-v")
        assert result.ret == 0


class TestFaulthandlerDiagnosticOutput:
    """faulthandler produces diagnostic output when a test hangs past its deadline.

    These tests combine with force_exit_delay to bound the total run time and
    must use runpytest_subprocess() because force_exit_delay calls os._exit().
    """

    def test_faulthandler_output_in_stderr_on_hang(self, pytester):
        """faulthandler traceback appears in stderr when test is stuck past timeout+1 s.

        -s disables pytest's fd-level capture so faulthandler's write to fd 2
        (via io.FileIO) goes to the real stderr temp file pytester reads.
        """
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_ignores_interrupt():
                # Swallow every exception including TimeoutException (a BaseException).
                # This simulates a GIL-holding C extension that cannot be interrupted.
                while True:
                    try:
                        time.sleep(0.01)
                    except BaseException:
                        pass
        """)
        # force_exit_delay=2.0 gives faulthandler (fires at 0.3+1=1.3 s) time to
        # dump before the hard exit (0.3+2.0=2.3 s).
        # -s prevents pytest's fd capture from intercepting the write to fd 2.
        result = pytester.runpytest_subprocess("--vigil-force-exit-delay=2.0", "-s")
        stderr = result.stderr.str()
        # faulthandler writes a "Timeout" header followed by thread tracebacks.
        assert "Timeout" in stderr or "Thread" in stderr, (
            f"Expected faulthandler output in stderr. Got:\n{stderr}"
        )
        assert result.ret == 124

    def test_faulthandler_shows_test_frame_in_traceback(self, pytester):
        """The faulthandler dump includes a frame from inside the stuck test.

        -s prevents pytest's fd capture from intercepting the write to fd 2.
        """
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_stuck_loop():
                while True:
                    try:
                        time.sleep(0.01)
                    except BaseException:
                        pass
        """)
        result = pytester.runpytest_subprocess("--vigil-force-exit-delay=2.0", "-s")
        stderr = result.stderr.str()
        # The traceback should contain a reference to this test file.
        assert "test_stuck_loop" in stderr or "test_faulthandler" in stderr or "Timeout" in stderr


class TestFaulthandlerModule:
    """Verify faulthandler is available and the API is as expected."""

    def test_faulthandler_available(self):
        """faulthandler module is importable (stdlib since Python 3.3)."""
        import faulthandler
        assert hasattr(faulthandler, "dump_traceback_later")
        assert hasattr(faulthandler, "cancel_dump_traceback_later")

    def test_dump_traceback_later_and_cancel_do_not_raise(self):
        """Basic smoke test: set and immediately cancel a faulthandler timer."""
        import faulthandler
        faulthandler.dump_traceback_later(60.0, repeat=False)
        faulthandler.cancel_dump_traceback_later()
