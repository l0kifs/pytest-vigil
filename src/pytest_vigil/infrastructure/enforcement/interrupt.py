"""Interruption logic for stopping tests."""

import os
import signal
import _thread
import sys
from loguru import logger

class Interrupter:
    """Handles the mechanism of interrupting a running test."""

    def trigger(self, reason: str) -> None:
        """Triggers the interruption."""
        logger.error(f"Test interruption triggered: {reason}")
        self._dump_stacks()
        
        if hasattr(signal, "SIGALRM"):
             # Send SIGALRM to self. 
             # The handler (registered in setup) should raise the exception.
             os.kill(os.getpid(), signal.SIGALRM)
        else:
             # Fallback
             _thread.interrupt_main()

    def _dump_stacks(self) -> None:
        import traceback
        code = []
        for threadId, stack in sys._current_frames().items():
            code.append(f"\n# Thread: {threadId}")
            for filename, lineno, name, line in traceback.extract_stack(stack):
                code.append(f'File: "{filename}", line {lineno}, in {name}')
                if line:
                    code.append(f"  {line}")
        logger.error("\n".join(code))
