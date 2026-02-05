"""System monitoring infrastructure using psutil."""

import os
import psutil
from typing import Tuple

class SystemMonitor:
    def __init__(self):
        self._process = psutil.Process(os.getpid())

    def get_stats(self) -> Tuple[float, float]:
        """
        Returns current process resource usage.
        
        Returns:
            Tuple[float, float]: (cpu_percent, memory_mb)
        """
        # cpu_percent(interval=None) is non-blocking and compares to last call
        # First call returns 0.0 usually, subsequent calls return avg since last call.
        cpu = self._process.cpu_percent(interval=None)
        
        mem_info = self._process.memory_info()
        # RSS is generic "Resident Set Size", good proxy for "how much memory this test added" 
        # in a naive way, though garbage collection complicates it.
        mem_mb = mem_info.rss / (1024 * 1024)
        
        return cpu, mem_mb
