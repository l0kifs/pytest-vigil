"""Session-level monitoring for global test run timeout."""

import os
import threading
import time
from typing import Optional, Callable
import psutil
from loguru import logger


class SessionMonitor:
    """Manages global timeout for the entire test session.
    
    Monitors the total execution time of a test run and terminates it if
    the global timeout is exceeded. First attempts graceful termination,
    then forcefully kills the process if needed. Properly handles cleanup
    of child processes including pytest-xdist workers.
    """

    def __init__(
        self,
        timeout: float,
        grace_period: float = 5.0,
        get_current_test: Optional[Callable[[], Optional[str]]] = None,
    ):
        """Initialize the session monitor.
        
        Args:
            timeout: Maximum duration in seconds for the test session
            grace_period: Time in seconds to wait for graceful termination before forcing
            get_current_test: Optional callback to retrieve currently executing test nodeid
        """
        self.timeout = timeout
        self.grace_period = grace_period
        self.get_current_test = get_current_test
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
        """Handle session timeout by terminating child processes and exiting."""
        import sys
        
        # Get currently executing test if available
        current_test = None
        if self.get_current_test:
            current_test = self.get_current_test()
        
        # Create detailed timeout message
        timeout_msg = f"\n{'='*70}\nSESSION TIMEOUT EXCEEDED ({self.timeout}s)\n{'='*70}\n"
        
        if current_test:
            timeout_msg += f"Currently executing test: {current_test}\n"
            logger.error(
                f"Session timeout exceeded ({self.timeout}s). "
                f"Currently executing test: {current_test}"
            )
        else:
            timeout_msg += "No test currently executing (or test tracking not available)\n"
            logger.error(f"Session timeout exceeded ({self.timeout}s)")
        
        timeout_msg += f"{'='*70}\n"
        
        # Write to stderr using file descriptor directly to bypass any buffering
        try:
            stderr_fd = 2
            os.write(stderr_fd, timeout_msg.encode('utf-8'))
        except Exception:
            # Fallback to sys.stderr if direct write fails
            sys.stderr.write(timeout_msg)
            sys.stderr.flush()
        
        # Terminate child processes first
        logger.info("Terminating child processes...")
        self._terminate_child_processes()
        
        # Give a brief moment for children to exit
        time.sleep(0.5)
        
        logger.error("Forcing test session to exit due to timeout")
        
        # Flush all output streams
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        
        # Use os._exit to force immediate termination from daemon thread
        # Exit code 124 is commonly used for timeout (like GNU timeout command)
        os._exit(124)

    def _terminate_child_processes(self) -> None:
        """Terminate all child processes including xdist workers."""
        try:
            current_process = psutil.Process(os.getpid())
            children = current_process.children(recursive=True)
            
            if children:
                logger.info(f"Terminating {len(children)} child process(es)...")
                for child in children:
                    try:
                        logger.debug(f"Terminating child process {child.pid}: {child.name()}")
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                    except Exception as e:
                        logger.warning(f"Error terminating child process {child.pid}: {e}")
                
                # Give children time to terminate gracefully
                gone, alive = psutil.wait_procs(children, timeout=3)
                
                if gone:
                    logger.debug(f"Successfully terminated {len(gone)} child process(es)")
                
                # Force kill any remaining children
                if alive:
                    logger.warning(f"Force killing {len(alive)} remaining child process(es)")
                    for child in alive:
                        try:
                            logger.debug(f"Force killing child process {child.pid}")
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass
                        except Exception as e:
                            logger.warning(f"Error killing child process {child.pid}: {e}")
                    
                    # Final wait to confirm
                    psutil.wait_procs(alive, timeout=1)
            else:
                logger.debug("No child processes to terminate")
        except Exception as e:
            logger.error(f"Error terminating child processes: {e}")


