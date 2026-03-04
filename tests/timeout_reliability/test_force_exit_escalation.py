"""
Tests for the force-exit escalation feature (Item 3).

When --vigil-force-exit-delay=N is set, vigil starts an escalation daemon
thread after the first soft interrupt.  If the test does not respond within N
seconds, os._exit(124) is called.

All tests that exercise os._exit() MUST use runpytest_subprocess() so that the
forceful exit kills the child process rather than the test-runner itself.
"""

import pytest

pytest_plugins = ["pytester"]

# Exit code produced by os._exit(124) inside the subprocess
_FORCE_EXIT_CODE = 124


class TestForceExitEscalationDisabledByDefault:
    """Without the option, no escalation happens."""

    def test_default_no_escalation_for_normal_timeout(self, pytester):
        """Normal timeout (test responds to interrupt) — no force exit, exit code 1."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_slow():
                time.sleep(2)
        """)
        result = pytester.runpytest()
        # Soft interrupt works; pytest reports a failure normally.
        assert result.ret == 1
        assert result.ret != _FORCE_EXIT_CODE

    def test_default_env_var_not_set(self, pytester, monkeypatch):
        """PYTEST_VIGIL__FORCE_EXIT_DELAY is not set by default."""
        monkeypatch.delenv("PYTEST_VIGIL__FORCE_EXIT_DELAY", raising=False)
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_slow():
                time.sleep(2)
        """)
        result = pytester.runpytest()
        assert result.ret == 1
        assert result.ret != _FORCE_EXIT_CODE


class TestForceExitEscalationTriggered:
    """When escalation is enabled and the interrupt is swallowed, force-exit fires."""

    def test_force_exit_when_interrupt_is_swallowed(self, pytester):
        """os._exit(124) is called when test catches TimeoutException via BaseException."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_swallows():
                while True:
                    try:
                        time.sleep(0.01)
                    except BaseException:
                        pass  # swallows vigil's interrupt
        """)
        # force_exit_delay=1.0 s — escalation fires 1 s after the soft interrupt.
        result = pytester.runpytest_subprocess("--vigil-force-exit-delay=1.0")
        assert result.ret == _FORCE_EXIT_CODE

    def test_force_exit_log_message_present(self, pytester):
        """The escalation log message appears in output before force-exit."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_ignores():
                while True:
                    try:
                        time.sleep(0.01)
                    except BaseException:
                        pass
        """)
        # -s disables pytest's fd-level capture so os.write(2, ...) in the
        # escalation thread goes to the real stderr temp file pytester reads.
        result = pytester.runpytest_subprocess("--vigil-force-exit-delay=1.0", "-s")
        full_output = result.stdout.str() + result.stderr.str()
        assert "soft interrupt was not handled" in full_output
        assert result.ret == _FORCE_EXIT_CODE

    def test_force_exit_respects_delay(self, pytester):
        """The process does not exit before the delay expires."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.2)
            def test_blocks():
                while True:
                    try:
                        time.sleep(0.01)
                    except BaseException:
                        pass
        """)
        import time
        t0 = time.monotonic()
        result = pytester.runpytest_subprocess("--vigil-force-exit-delay=1.5")
        elapsed = time.monotonic() - t0
        # Should take at least: test timeout (0.2) + escalation delay (1.5) ≈ 1.7 s
        assert elapsed >= 1.5
        assert result.ret == _FORCE_EXIT_CODE


class TestForceExitEscalationCancelled:
    """When the test responds normally to the interrupt, escalation is cancelled."""

    def test_no_force_exit_when_interrupt_is_handled(self, pytester):
        """A test that times out normally (interrupt propagates) is not force-exited."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_normal_timeout():
                time.sleep(2)
        """)
        result = pytester.runpytest_subprocess("--vigil-force-exit-delay=5.0")
        # Soft interrupt fires, test fails with exit code 1 — NOT 124.
        assert result.ret == 1
        assert result.ret != _FORCE_EXIT_CODE

    def test_no_force_exit_for_passing_test(self, pytester):
        """A passing test is never escalated."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=2.0)
            def test_passes():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest_subprocess("--vigil-force-exit-delay=0.5")
        assert result.ret == 0
        assert result.ret != _FORCE_EXIT_CODE

    def test_second_test_not_force_exited_after_first_timeout(self, pytester):
        """Escalation from test-1 is cancelled before test-2 starts."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.3)
            def test_times_out():
                time.sleep(2)

            @pytest.mark.vigil(timeout=2.0)
            def test_passes_after():
                time.sleep(0.05)
                assert True
        """)
        result = pytester.runpytest_subprocess("--vigil-force-exit-delay=5.0")
        # First test fails, second passes; if escalation leaked the whole
        # process would exit with 124 before the second test finishes.
        assert result.ret == 1          # pytest failure exit code
        assert result.ret != _FORCE_EXIT_CODE
        result.assert_outcomes(passed=1, failed=1)


class TestForceExitEscalationConfiguration:
    """The feature is configurable via CLI option and environment variable."""

    def test_cli_option_enables_escalation(self, pytester):
        """--vigil-force-exit-delay enables the feature."""
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.2)
            def test_swallows():
                while True:
                    try:
                        time.sleep(0.01)
                    except BaseException:
                        pass
        """)
        result = pytester.runpytest_subprocess("--vigil-force-exit-delay=1.0")
        assert result.ret == _FORCE_EXIT_CODE

    def test_env_var_enables_escalation(self, pytester, monkeypatch):
        """PYTEST_VIGIL__FORCE_EXIT_DELAY environment variable enables the feature."""
        monkeypatch.setenv("PYTEST_VIGIL__FORCE_EXIT_DELAY", "1.0")
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.2)
            def test_swallows():
                while True:
                    try:
                        time.sleep(0.01)
                    except BaseException:
                        pass
        """)
        result = pytester.runpytest_subprocess()
        assert result.ret == _FORCE_EXIT_CODE

    def test_cli_overrides_env_var(self, pytester, monkeypatch):
        """CLI option value takes precedence over the environment variable."""
        # env says 60 s (would not fire during test), CLI says 1 s (will fire)
        monkeypatch.setenv("PYTEST_VIGIL__FORCE_EXIT_DELAY", "60.0")
        pytester.makepyfile("""
            import pytest
            import time

            @pytest.mark.vigil(timeout=0.2)
            def test_swallows():
                while True:
                    try:
                        time.sleep(0.01)
                    except BaseException:
                        pass
        """)
        result = pytester.runpytest_subprocess("--vigil-force-exit-delay=1.0")
        assert result.ret == _FORCE_EXIT_CODE


class TestInterrupterUnit:
    """Unit tests for Interrupter escalation logic."""

    def test_cancel_escalation_before_trigger_is_safe(self):
        """Calling cancel_escalation() before trigger() should not raise."""
        from pytest_vigil.infrastructure.enforcement.interrupt import Interrupter
        i = Interrupter(force_exit_delay=10.0)
        i.cancel_escalation()  # must not raise

    def test_no_escalation_thread_without_force_exit_delay(self):
        """No escalation thread is started when force_exit_delay is None."""
        from pytest_vigil.infrastructure.enforcement.interrupt import Interrupter
        i = Interrupter(force_exit_delay=None)
        # Do not actually send a signal; just verify no thread was created.
        assert i._escalation_thread is None

    def test_escalation_cancel_event_set_by_cancel(self):
        """cancel_escalation() sets the internal event."""
        from pytest_vigil.infrastructure.enforcement.interrupt import Interrupter
        i = Interrupter(force_exit_delay=10.0)
        assert not i._escalation_cancel.is_set()
        i.cancel_escalation()
        assert i._escalation_cancel.is_set()
