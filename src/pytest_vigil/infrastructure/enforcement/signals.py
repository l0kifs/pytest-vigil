"""Signal handling infrastructure."""

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

    def restore(self) -> None:
        if hasattr(signal, "SIGALRM") and self._old_handler is not None:
            signal.signal(signal.SIGALRM, self._old_handler)
            self._old_handler = None
