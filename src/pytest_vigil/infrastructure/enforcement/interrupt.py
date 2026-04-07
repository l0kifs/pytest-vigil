"""Interruption logic for stopping tests."""

import os
import signal
import _thread
import sys
import threading
from typing import Optional
from pytest_vigil.infrastructure.observability.logging import get_logger

log = get_logger(__name__)


class Interrupter:
    """Handles the mechanism of interrupting a running test."""

    def __init__(self, force_exit_delay: Optional[float] = None):
        """Initialize the interrupter.

        Args:
            force_exit_delay: If set, start a daemon escalation thread after the
                first trigger() call.  If the test does not respond within this
                many seconds (i.e. the soft interrupt was ignored — e.g. by
                GIL-holding C-extension code or by a bare ``except BaseException``
                block), call ``os._exit(124)`` to force-terminate the process.
                ``None`` (default) disables escalation entirely.
        """
        self._force_exit_delay = force_exit_delay
        self._escalation_thread: Optional[threading.Thread] = None
        self._escalation_cancel = threading.Event()

    def trigger(self, reason: str) -> None:
        """Trigger a soft interrupt in the main thread."""
        # Write directly to fd 2 so the message is always visible regardless of
        # pytest's per-test log capture state (monitor thread timing race).
        try:
            os.write(2, f"vigil.interrupter: test interruption triggered: {reason}\n".encode("utf-8", errors="replace"))
        except Exception:
            pass
        log.error("vigil.interrupter: test interruption triggered: %s", reason)
        self._dump_stacks()

        if hasattr(signal, "SIGALRM"):
            # Send SIGALRM to self.
            # The handler (registered in setup) should raise TimeoutException.
            os.kill(os.getpid(), signal.SIGALRM)
        else:
            # Fallback for Windows: raises KeyboardInterrupt in the main thread.
            _thread.interrupt_main()

        # Start escalation timer on first trigger if the feature is enabled.
        if self._force_exit_delay is not None and self._escalation_thread is None:
            self._escalation_cancel.clear()
            self._escalation_thread = threading.Thread(
                target=self._escalation_run,
                daemon=True,
                name="vigil-escalation",
            )
            self._escalation_thread.start()

    def cancel_escalation(self) -> None:
        """Cancel any pending force-exit escalation.

        Call this as soon as the test finishes (even after a timeout), to prevent
        the escalation from firing after the test run has already moved on to the
        next test or teardown.
        """
        self._escalation_cancel.set()

    def _escalation_run(self) -> None:
        """Daemon thread: force-exit if the soft interrupt is not handled in time."""
        if self._escalation_cancel.wait(self._force_exit_delay):
            log.debug("vigil.interrupter: escalation cancelled — interrupt was handled in time")
            return

        msg = (
            f"\nVigil: soft interrupt was not handled after {self._force_exit_delay}s. "
            "This usually means the test is stuck inside a C extension that holds "
            "the GIL, or the TimeoutException was silently caught. Forcing exit.\n"
        )
        # Write directly to fd 2 so the message survives os._exit() even when
        # Python-level stderr is buffered or captured by pytest.
        try:
            os.write(2, msg.encode("utf-8", errors="replace"))
        except Exception:
            pass
        self._dump_stacks()
        os._exit(124)

    def _dump_stacks(self) -> None:
        import traceback
        code = []
        for threadId, stack in sys._current_frames().items():
            code.append(f"\n# Thread: {threadId}")
            for filename, lineno, name, line in traceback.extract_stack(stack):
                code.append(f'File: "{filename}", line {lineno}, in {name}')
                if line:
                    code.append(f"  {line}")
        log.error("vigil.interrupter: stack dump", stack="\n".join(code))
