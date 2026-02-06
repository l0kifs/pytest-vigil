"""Session-level monitoring for global test run timeout."""

import os
import signal
import threading
import time
from typing import Optional
from loguru import logger


class SessionMonitor:
    """Manages global timeout for the entire test session.
    
    Monitors the total execution time of a test run and terminates it if
    the global timeout is exceeded. First attempts graceful termination,
    then forcefully kills the process if needed.
    """

    def __init__(
        self,
        timeout: float,
        grace_period: float = 5.0,
    ):
        """Initialize the session monitor.
        
        Args:
            timeout: Maximum duration in seconds for the test session
            grace_period: Time in seconds to wait for graceful termination before forcing
        """
        self.timeout = timeout
        self.grace_period = grace_period
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None

    def start(self) -> None:
        """Start the session monitoring thread."""
        self._start_time = time.time()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="vigil-session-monitor"
        )
        self._thread.start()
        logger.info(f"Session monitor started with timeout of {self.timeout}s")

    def stop(self) -> None:
        """Stop the session monitoring thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.debug("Session monitor stopped")

    def _run(self) -> None:
        """Main monitoring loop."""
        if self._start_time is None:
            logger.error("Session monitor started without start_time")
            return
            
        while not self._stop_event.is_set():
            elapsed = time.time() - self._start_time
            remaining = self.timeout - elapsed

            if remaining <= 0:
                self._handle_timeout()
                break

            # Check every second or at the remaining time, whichever is shorter
            sleep_time = min(1.0, remaining)
            self._stop_event.wait(sleep_time)

    def _handle_timeout(self) -> None:
        """Handle session timeout by attempting graceful then forceful termination."""
        pid = os.getpid()
        logger.error(
            f"Session timeout exceeded ({self.timeout}s). "
            f"Attempting graceful termination..."
        )

        # Attempt graceful termination
        try:
            if hasattr(signal, "SIGTERM"):
                logger.warning(f"Sending SIGTERM to process {pid}")
                os.kill(pid, signal.SIGTERM)
            elif hasattr(signal, "SIGINT"):
                logger.warning(f"Sending SIGINT to process {pid}")
                os.kill(pid, signal.SIGINT)
            else:
                # No graceful signal available, go straight to forceful
                logger.warning("No graceful termination signal available")
                self._force_kill()
                return
        except Exception as e:
            logger.error(f"Error during graceful termination: {e}")
            self._force_kill()
            return

        # Wait for grace period
        logger.info(f"Waiting {self.grace_period}s for graceful shutdown...")
        time.sleep(self.grace_period)

        # If we're still running, force kill
        if not self._stop_event.is_set():
            self._force_kill()

    def _force_kill(self) -> None:
        """Forcefully terminate the test run process."""
        pid = os.getpid()
        logger.error(
            f"Forcefully terminating test run after grace period. "
            f"Sending SIGKILL to process {pid}"
        )
        try:
            if hasattr(signal, "SIGKILL"):
                os.kill(pid, signal.SIGKILL)
            else:
                # Fallback for systems without SIGKILL
                logger.error("SIGKILL not available, using sys.exit()")
                import sys
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error during forced termination: {e}")
            import sys
            sys.exit(1)
