"""Session-level monitoring for global test run timeout."""

import os
import threading
import time
from typing import Optional, Callable
import psutil
from pytest_vigil.infrastructure.observability.logging import get_logger

log = get_logger(__name__)


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
        get_last_test: Optional[Callable[[], Optional[str]]] = None,
    ):
        """Initialize the session monitor.
        
        Args:
            timeout: Maximum duration in seconds for the test session
            grace_period: Time in seconds to wait for graceful termination before forcing
            get_current_test: Optional callback to retrieve currently executing test nodeid
            get_last_test: Optional callback to retrieve last executed test nodeid
        """
        self.timeout = timeout
        self.grace_period = grace_period
        self.get_current_test = get_current_test
        self.get_last_test = get_last_test
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
        log.info("vigil.session_monitor: started", timeout=self.timeout)

    def stop(self) -> None:
        """Stop the session monitoring thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        log.debug("vigil.session_monitor: stopped")

    def _run(self) -> None:
        """Main monitoring loop."""
        if self._start_time is None:
            log.error("vigil.session_monitor: started without start_time")
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
        
        # Get last executed test if available
        last_test = None
        if self.get_last_test:
            last_test = self.get_last_test()
        
        # Create detailed timeout message
        timeout_msg = f"\n{'='*70}\nSESSION TIMEOUT EXCEEDED ({self.timeout}s)\n{'='*70}\n"
        
        if current_test:
            timeout_msg += f"Currently executing test: {current_test}\n"
            log.error("vigil.session_monitor: session timeout exceeded", timeout=self.timeout, current_test=current_test)
        elif last_test:
            timeout_msg += f"Last executed test: {last_test}\n"
            timeout_msg += "(Timeout occurred between tests)\n"
            log.error("vigil.session_monitor: session timeout exceeded", timeout=self.timeout, last_test=last_test)
        else:
            timeout_msg += "No test currently executing (or test tracking not available)\n"
            log.error("vigil.session_monitor: session timeout exceeded", timeout=self.timeout)
        
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
        log.info("vigil.session_monitor: terminating child processes")
        self._terminate_child_processes()
        
        # Give a brief moment for children to exit
        time.sleep(0.5)
        
        log.error("vigil.session_monitor: forcing test session to exit due to timeout")
        
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
                log.info("vigil.session_monitor: terminating child processes", count=len(children))
                for child in children:
                    try:
                        log.debug("vigil.session_monitor: terminating child process", pid=child.pid, name=child.name())
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                    except Exception as e:
                        log.warning("vigil.session_monitor: error terminating child process", pid=child.pid)
                
                # Give children time to terminate gracefully
                gone, alive = psutil.wait_procs(children, timeout=3)
                
                if gone:
                    log.debug("vigil.session_monitor: terminated child processes", count=len(gone))
                
                # Force kill any remaining children
                if alive:
                    log.warning("vigil.session_monitor: force killing remaining child processes", count=len(alive))
                    for child in alive:
                        try:
                            log.debug("vigil.session_monitor: force killing child process", pid=child.pid)
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass
                        except Exception as e:
                            log.warning("vigil.session_monitor: error killing child process", pid=child.pid)
                    
                    # Final wait to confirm
                    psutil.wait_procs(alive, timeout=1)
            else:
                log.debug("vigil.session_monitor: no child processes to terminate")
        except Exception:
            log.exception("vigil.session_monitor: error terminating child processes")


