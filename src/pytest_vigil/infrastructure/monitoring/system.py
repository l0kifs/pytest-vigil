"""System monitoring infrastructure using psutil."""

import os
import psutil
from typing import Tuple, Dict
from loguru import logger

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

    def get_detailed_stats(self) -> Tuple[float, float, Dict[str, float]]:
        """
        Returns detailed process resource usage with breakdown by process type.
        
        Returns:
            Tuple[float, float, Dict[str, float]]: (total_cpu_percent, memory_mb, cpu_breakdown)
            cpu_breakdown is a dict mapping process type to CPU percentage
        """
        # Get main process stats first
        main_cpu = self._process.cpu_percent(interval=None)
        mem_info = self._process.memory_info()
        mem_mb = mem_info.rss / (1024 * 1024)
        
        # Initialize breakdown with main process
        cpu_breakdown = {"pytest": main_cpu}
        total_cpu = main_cpu
        
        try:
            # Only check for children if we have any
            # Use non-recursive check first for performance
            num_children = self._process.num_threads()  # Quick check
            if num_children > 1:  # More than just the main thread
                # Get all child processes
                children = self._process.children(recursive=True)
                
                # Categorize and sum CPU by process type
                for child in children:
                    try:
                        child_cpu = child.cpu_percent(interval=None)
                        if child_cpu > 0.0:  #Only count processes with actual CPU usage
                            total_cpu += child_cpu
                            
                            # Categorize process by name
                            process_type = self._categorize_process(child)
                            cpu_breakdown[process_type] = cpu_breakdown.get(process_type, 0.0) + child_cpu
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        # Process may have terminated or is not accessible
                        continue
            
        except Exception as e:
            logger.debug(f"Error collecting child process stats: {e}")
            # Continue with main process stats only
        
        return total_cpu, mem_mb, cpu_breakdown
    
    def _categorize_process(self, process: psutil.Process) -> str:
        """
        Categorize a process by its name/command line.
        
        Returns process type: browser, gpu, network, renderer, python, or other
        """
        try:
            name = process.name().lower()
            cmdline = " ".join(process.cmdline()).lower()
            
            # Browser processes
            if any(browser in name for browser in ["chrome", "chromium", "firefox", "safari", "edge"]):
                # More specific categorization for Chromium-based browsers
                if "gpu-process" in cmdline or "--type=gpu-process" in cmdline:
                    return "gpu"
                elif "renderer" in cmdline or "--type=renderer" in cmdline:
                    return "renderer"
                elif "network" in cmdline or "--type=utility" in cmdline:
                    return "network"
                else:
                    return "browser"
            
            # WebDriver/Selenium
            if any(driver in name for driver in ["geckodriver", "chromedriver", "safaridriver"]):
                return "webdriver"
            
            # Python subprocesses
            if "python" in name:
                return "python"
            
            # Playwright/Puppeteer
            if "playwright" in cmdline or "puppeteer" in cmdline:
                return "automation"
            
            # Default
            return "other"
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "other"
