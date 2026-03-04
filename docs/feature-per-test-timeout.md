# Per-test Timeout Feature

## 🔒 Interrupt Reliability

When a timeout fires, Vigil uses a layered approach to ensure the test is actually stopped — even when standard Python signal delivery is unreliable.

### Layer 1 — Monitoring thread (always active)

A background thread polls resource usage every `MONITOR_INTERVAL` seconds (default 0.1 s). When a limit is exceeded it sends either `SIGALRM` (Unix) or `KeyboardInterrupt` (Windows) to the main thread, which raises `TimeoutException` in the test.

### Layer 2 — Kernel alarm backstop (Unix only, automatic)

When a test timeout is set, Vigil also arms `signal.alarm()` — a POSIX kernel timer. This fires independently of the monitoring thread, so the test is still interrupted even if the monitoring thread is delayed or dead. The alarm fires at `ceil(timeout)` seconds and is cancelled as soon as the test finishes.

### Layer 3 — Faulthandler diagnostics (automatic when timeout is set)

Python's `faulthandler` module is armed at `timeout + 1 s`. If the test is still running at that point (because the interrupt was silently swallowed), faulthandler writes C-level tracebacks for all threads directly to `stderr`. This output survives even when Python is blocked inside a C extension.

### Layer 4 — Force-exit escalation (opt-in)

Some tests cannot be interrupted at all: those stuck inside a native C extension that holds the Python GIL, or tests with a bare `except BaseException: pass` that swallow `TimeoutException`. For these, use `--vigil-force-exit-delay`:

```bash
# Force-exit the process 2 s after the soft interrupt if the test is still running
pytest --vigil-timeout 5 --vigil-force-exit-delay 2
```

When the delay expires, Vigil calls `os._exit(124)` — an immediate process termination that bypasses all Python cleanup. The exit code 124 follows the GNU `timeout` command convention and can be detected in CI.

> **Note:** `--vigil-force-exit-delay` terminates the **entire pytest process**. Use it only when you know a test can get permanently stuck and are willing to sacrifice the remainder of the run.

```bash
# Via environment variable (useful for CI pipelines)
export PYTEST_VIGIL__FORCE_EXIT_DELAY=2.0
pytest --vigil-timeout 5
```