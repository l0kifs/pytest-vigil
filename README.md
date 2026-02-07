<div align="center">

![pytest-vigil](https://socialify.git.ci/l0kifs/pytest-vigil/image?description=0&font=Inter&language=1&name=1&owner=1&pattern=Signal&theme=Light)

# Pytest Vigil

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
![GitHub last commit](https://img.shields.io/github/last-commit/l0kifs/pytest-vigil)
![GitHub Release Date](https://img.shields.io/github/release-date/l0kifs/pytest-vigil?label=last%20release)

</div>

**Pytest Vigil** is a reliability pytest plugin that enforces resource limits on your tests and kills them when they exceed those limits.

### Why you might need this

- Tests sometimes hang indefinitely due to deadlocks or infinite loops
- Memory leaks crash your test runner or CI environment
- CPU-intensive tests slow down your entire suite
- You want to enforce maximum runtime for your CI pipeline
- You need to identify which tests are resource hogs

---

## ✨ Features

- 👮 **Resource Guard**: Enforce hard limits on **Time**, **Memory** (MB), and **CPU** (%).
- 🧟 **Stall Detective**: Automatically detect and kill deadlocked tests (monitoring low CPU).
- ⏱️ **Session Enforcer**: Set a global timeout for the entire suite with graceful shutdown.
- 🤖 **CI Native**: Auto-scales limits (default `2x`) when running in CI environments.
- 🔄 **Flake Manager**: Built-in retry mechanism for tests that violate resource limits.
- 🔬 **Forensic Reporting**: JSON reports with deep CPU breakdown (Browser vs Renderer vs GPU).

## 🚀 Installation

```bash
uv add -D pytest-vigil
# or
pip install pytest-vigil
```

## ⚡ Quick Start

**1. Protect against heavy tests**
Limit tests to 5 seconds, 512MB RAM, and 80% CPU:
```bash
pytest --vigil-timeout 5 --vigil-memory 512 --vigil-cpu 80
```

**2. Prevent infinite CI hangs**
Kill the entire suite if it runs longer than 15 minutes:
```bash
pytest --vigil-session-timeout 900
```

**3. Generate Reliability Report**
```bash
pytest --vigil-report reliability.json
```

## 🛠 Usage & Configuration

### CLI Options Reference

| Option | Default | Description |
|--------|---------|-------------|
| `--vigil-timeout` | `None` | Max duration per test (seconds) |
| `--vigil-memory` | `None` | Max memory usage (MB) |
| `--vigil-cpu` | `None` | Max CPU usage (%) |
| `--vigil-retry` | `0` | Auto-retry failed/limit-violating tests |
| `--vigil-stall-timeout` | `None` | Max duration of low CPU (deadlock detection) |
| `--vigil-session-timeout` | `None` | Global timeout for entire test run |
| `--vigil-report` | `None` | Path to save JSON reliability report |
| `--vigil-cli-report-verbosity` | `short` | Terminal output: `none`, `short`, `full` |

### Using Markers

Apply specific limits to critical or heavy tests directly in code. All arguments are optional.

| Parameter | Type | Unit | Default | Description |
|-----------|------|------|---------|-------------|
| `timeout` | `float` | `s` | `None` | Test timeout |
| `memory` | `float` | `MB` | `None` | Memory limit |
| `cpu` | `float` | `%` | `None` | CPU limit |
| `retry` | `int` | - | `0` | Number of retries on failure |
| `stall_timeout` | `float` | `s` | `None` | Max duration of low CPU activity |
| `stall_cpu_threshold`| `float` | `%` | `1.0` | CPU threshold for stall detection |

```python
import pytest

@pytest.mark.vigil(timeout=5.0, memory=512, retry=2)
def test_heavy_computation():
    ...
```

### Environment Variables

Perfect for CI/CD pipelines. All options are available via `PYTEST_VIGIL__*` prefix.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PYTEST_VIGIL__TIMEOUT` | `None` | Default test timeout (seconds) |
| `PYTEST_VIGIL__MEMORY_LIMIT_MB` | `None` | Default memory limit (MB) |
| `PYTEST_VIGIL__CPU_LIMIT_PERCENT` | `None` | Default CPU limit (%) |
| `PYTEST_VIGIL__SESSION_TIMEOUT` | `None` | Global suite timeout (seconds) |
| `PYTEST_VIGIL__SESSION_TIMEOUT_GRACE_PERIOD` | `5.0` | Seconds to wait for graceful shutdown |
| `PYTEST_VIGIL__MONITOR_INTERVAL` | `0.1` | Internal check frequency (seconds) |
| `PYTEST_VIGIL__STRICT_MODE` | `True` | Enforce strict monitoring |
| `PYTEST_VIGIL__CI_MULTIPLIER` | `2.0` | Limit multiplier for CI environments |
| `PYTEST_VIGIL__RETRY_COUNT` | `0` | Number of retries for failures |
| `PYTEST_VIGIL__STALL_TIMEOUT` | `None` | Low-CPU deadlock timeout (seconds) |
| `PYTEST_VIGIL__STALL_CPU_THRESHOLD` | `1.0` | Threshold (%) for stall detection |
| `PYTEST_VIGIL__REPORT_VERBOSITY` | `short` | Terminal output: `none`, `short`, `full` |

## 📊 Reporting

Vigil provides insights into where your resources are going.

### Terminal Report
Control verbosity with `--vigil-cli-report-verbosity` (`none`, `short`, `full`).

**Short Mode (Default):**
```text
Vigil Reliability Report
Total Tests: 953 | Avg Duration: 5.32s | Avg Memory: 288.6 MB

Peak CPU by Process Type:
  Browser: 3542.1%  (Chromium/Webkit)
  Renderer: 2156.8% (Tab rendering)
  Pytest: 593.5%    (Test logic)
```

**Full Mode:**
```text
Vigil Reliability Report
Test ID                                                 Att Duration (s)  Max CPU (%) Max Mem (MB)
--------------------------------------------------------------------------------------------------
tests/test_stress.py::test_high_load                      0         8.42        450.5        820.1
tests/test_ui.py::test_login[chromium]                    0         4.15       2101.2        415.8
tests/test_ui.py::test_checkout[chromium]                 1        12.30       3542.1        590.4
tests/test_api.py::test_latency                           0         0.25         15.2         45.1
```

> **💡 Note on CPU > 100%:**
> In multi-process testing (like Playwright/Selenium), usage is summed across all cores and child processes. 7000% CPU usage means your test suite is utilizing ~70 cores efficiently (or inefficiently!).

### JSON Report
The JSON report captures `cpu_breakdown` for every test, helping you identify if it's the **Browser**, **DB**, or **Python** code causing the spike.

**Key Fields:**
- `flaky_tests`: Tests that passed after retry (attempt > 0)
- `cpu_breakdown`: Peak CPU by process type (`pytest`, `browser`, `renderer`, `gpu`, `webdriver`, `python`, `automation`)
- `limits`: Applied resource constraints from CLI/markers/env

<details>
<summary>📄 <b>Example JSON Report</b> (click to expand)</summary>

```json
{
  "timestamp": "2026-02-08T14:23:45.123456+00:00",
  "flaky_tests": [
    "tests/test_integration.py::test_api_retry"
  ],
  "results": [
    {
      "node_id": "tests/test_ui.py::test_checkout[chromium]",
      "attempt": 0,
      "duration": 12.34,
      "max_cpu": 3542.1,
      "max_memory": 590.4,
      "cpu_breakdown": {
        "pytest": 89.2,
        "browser": 1805.3,
        "renderer": 1247.6,
        "gpu": 400.0
      },
      "limits": [
        {
          "limit_type": "time",
          "threshold": 15.0,
          "secondary_threshold": null,
          "strict": true
        },
        {
          "limit_type": "memory",
          "threshold": 1024.0,
          "secondary_threshold": null,
          "strict": true
        }
      ]
    },
    {
      "node_id": "tests/test_integration.py::test_api_retry",
      "attempt": 1,
      "duration": 2.15,
      "max_cpu": 45.8,
      "max_memory": 128.3,
      "cpu_breakdown": {
        "pytest": 45.8
      },
      "limits": [
        {
          "limit_type": "time",
          "threshold": 5.0,
          "secondary_threshold": null,
          "strict": true
        }
      ]
    }
  ]
}
```

</details>

## ⚖️ License
MIT
