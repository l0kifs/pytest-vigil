# Vigil Feature List

## Current Business Features

| Feature | Description |
|---|---|
| Per-test resource limits | Kill tests exceeding `timeout`, `memory`, or `cpu` |
| Stall / deadlock detection | Kill tests stuck at low CPU for too long |
| Session timeout | Kill the entire suite after a global time limit |
| CI scaling | Auto-multiply limits by `ci_multiplier` in CI environments |
| Retry mechanism | Re-run tests that fail or violate limits, up to N times |
| Marker-based config | `@pytest.mark.vigil()` for per-test overrides |
| Env var config | `PYTEST_VIGIL__*` prefix for all settings |
| CLI terminal report | `short` / `full` verbosity with flaky test detection |
| JSON report | Per-test stats with `cpu_breakdown` by process type |
| pytest-xdist support | Aggregates results across parallel workers |

---

## Possible New Features

### 1. Limit violation cause tracking
**Problem:** The JSON report records `limits` (what was configured) but never records *which* limit was actually violated when a test was killed. The `TestOutcome` enum already has `TIMEOUT` and `RESOURCE_ERROR` values that go unused.
**Suggestion:** Add a `violation` field to each result entry (`"violation": {"type": "memory", "measured": 1340.2, "threshold": 1024.0}`).

---

### 2. Warn-only (non-strict) mode per limit
**Problem:** Limits are all-or-nothing — either the test is killed or nothing happens.
**Suggestion:** Add a `strict` parameter to the marker and a `--vigil-warn` CLI flag that records violations in the report without interrupting the test. This enables gradual rollout of limits in existing test suites.

```python
@pytest.mark.vigil(timeout=5.0, strict=False)  # warn but don't kill
```

---

### 3. Slow test warning threshold
**Problem:** `--vigil-timeout` kills tests; there is no way to just *flag* slow tests.
**Suggestion:** `--vigil-slow <seconds>` — marks tests exceeding the threshold as `[SLOW]` in both terminal and JSON reports without killing them, useful for performance regression awareness.

---

### 4. Memory leak detection
**Problem:** A test may stay within its per-test memory limit but leak memory across the session, causing later tests to OOM.
**Suggestion:** Track process memory before and after each test. If post-test memory is significantly higher than pre-test memory (e.g., >10 MB net gain), flag the test as a `potential_memory_leak` in the report.

---

### 5. Warning thresholds (soft limits)
**Problem:** Users cannot get early warnings before a limit is hit, only after the test is killed.
**Suggestion:** Add a `warn_at` parameter (percentage of limit, e.g., 80%) that prints a warning to the terminal when a test is approaching its limit, without killing it.

---

### 6. pyproject.toml / `pytest.ini` configuration support
**Problem:** Configuration requires env vars or CLI flags. There is no native pytest INI integration.
**Suggestion:** Support `[tool.pytest.ini_options]` (or a `[vigil]` section) so teams can commit default limits to the repo directly.

```toml
[tool.pytest.vigil]
timeout = 10
memory = 512
retry = 1
```

---

### 7. Per-test violation history in terminal report
**Problem:** The terminal report shows aggregate stats but does not call out tests that were actually killed.
**Suggestion:** Add a "Violations" section to the terminal report listing every test that was interrupted, the violated limit, and the measured value at the time of violation.

---

### 8. Process count limit
**Problem:** A test may spawn excessive child processes (e.g., via `subprocess` or `multiprocessing`) without CPU or memory limits being triggered.
**Suggestion:** `--vigil-max-processes <N>` / `max_processes` marker parameter that kills a test spawning more than N child processes.

---

### 9. HTML report
**Problem:** The JSON report is machine-readable but not human-friendly for post-run review.
**Suggestion:** `--vigil-html-report <path>` generating an HTML page with sortable tables, resource timeline sparklines per test, and a top-N slowest/most-memory-hungry test list.

---

### 10. Flaky test resource diff
**Problem:** Flaky tests are identified (passed after retry) but there is no analysis of *why* they were flaky.
**Suggestion:** For tests in `flaky_tests`, include a `resource_diff` in the JSON comparing resource usage between the failed attempt and the passing attempt (e.g., the first attempt used 3× more CPU).

---

### 11. Subprocess isolation mode
The only way to guarantee per-test timeout works against any code is to run each test in a subprocess and kill it with SIGKILL. The parent process is immune to GIL, signal masking, C extensions — the subprocess just dies.

This is what pytest-xdist effectively provides when each worker gets one test. You could add --vigil-subprocess mode that runs each test via subprocess.run(["pytest", "--collect-only", item.nodeid, ...]) with a timeout= parameter.

Real cost: subprocess startup overhead (0.1–0.5s per test), session-scoped fixtures can't be shared, adds complexity. Makes sense as an opt-in mode for tests known to use unsafe C extensions.