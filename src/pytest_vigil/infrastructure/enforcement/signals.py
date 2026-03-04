"""Signal handling infrastructure."""

import math
import signal
from typing import Any, Optional

class TimeoutException(BaseException):
    """Exception raised when a test times out."""
    pass

def timeout_signal_handler(signum: int, frame: Any) -> None:
    """Signal handler that raises TimeoutException."""
    raise TimeoutException("Test timed out (Vigil)")

class SignalManager:
    def __init__(self):
        self._old_handler: Optional[Any] = None

    def install(self) -> None:
        if hasattr(signal, "SIGALRM"):
            self._old_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)

    def set_alarm(self, timeout: float) -> None:
        """Set a kernel-level SIGALRM timer as a hard backstop (Unix only).

        This fires even if the monitoring thread has died or is delayed, because
        the delivery is handled entirely by the OS — no Python thread required.
        Uses integer-second granularity; rounds the timeout up to the nearest
        whole second (minimum 1 s).
        """
        if hasattr(signal, "SIGALRM"):
            signal.alarm(max(1, math.ceil(timeout)))

    def cancel_alarm(self) -> None:
        """Cancel any pending SIGALRM alarm (Unix only)."""
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)

    def restore(self) -> None:
        if hasattr(signal, "SIGALRM") and self._old_handler is not None:
            signal.alarm(0)  # cancel any pending alarm before restoring the old handler
            signal.signal(signal.SIGALRM, self._old_handler)
            self._old_handler = None
