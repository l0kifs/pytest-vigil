<div align="center">

![pytest-vigil](https://socialify.git.ci/l0kifs/pytest-vigil/image?description=0&font=Inter&language=1&name=1&owner=1&pattern=Signal&theme=Light)

# Pytest Vigil - Reliability Vigilance for Pytest

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
![GitHub last commit](https://img.shields.io/github/last-commit/l0kifs/pytest-vigil)
![GitHub Release Date](https://img.shields.io/github/release-date/l0kifs/pytest-vigil?label=last%20release)
![GitHub repo size](https://img.shields.io/github/repo-size/l0kifs/pytest-vigil)

</div>

## Features

- **Resource Enforcement**: Set hard limits on **Time**, **Memory** (MB), and **CPU** (%).
- **Stall Detection**: Detects deadlocks by monitoring low CPU usage over time.
- **Global Session Timeout**: Set a maximum duration for the entire test run, with graceful and forceful termination.
- **CI Awareness**: Automatically scales limits (default `2x`) when running in CI environments.
- **Flake Management**: Built-in retry mechanism for failed or resource-violating tests.
- **Detailed Reporting**: Generates JSON reports with resource usage metrics.
- **Debug context**: Dumps thread stacks upon timeout/interrupt.

## Installation

```bash
uv add -D pytest-vigil
# or
pip install pytest-vigil
```

## Usage

### CLI Options

| Option | Unit | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--vigil-timeout` | `s` | No | `None` | Test timeout |
| `--vigil-memory` | `MB` | No | `None` | Memory limit |
| `--vigil-cpu` | `%` | No | `None` | CPU limit |
| `--vigil-retry` | - | No | `0` | Number of retries on failure |
| `--vigil-stall-timeout` | `s` | No | `None` | Max duration of low CPU activity |
| `--vigil-stall-cpu-threshold` | `%` | No | `1.0` | CPU threshold for stall detection |
| `--vigil-session-timeout` | `s` | No | `None` | Global timeout for entire test run |
| `--vigil-session-timeout-grace-period` | `s` | No | `5.0` | Grace period before forceful termination |
| `--vigil-report` | - | No | `None` | Path to JSON report file |
| `--vigil-cli-report-verbosity` | - | No | `short` | Terminal report display: `none`, `short` (summary), `full` |

```bash
pytest --vigil-timeout 5 --vigil-memory 512 --vigil-cpu 80
```

### Terminal Report Verbosity

Control how much of the reliability report is displayed in the terminal. Available options:

- **`none`**: No reliability report displayed (useful for CI pipelines where you only need JSON reports)
- **`short`**: Display summary statistics only (total tests, averages, fastest/slowest tests)
- **`full`**: Display detailed table with all tests (default behavior)

```bash
# Hide terminal report completely
pytest --vigil-cli-report-verbosity none

# Show summary statistics only (default)
pytest --vigil-cli-report-verbosity short

# Show all tests in detailed table
pytest --vigil-cli-report-verbosity full
```

**Configuration**:
- CLI: `--vigil-cli-report-verbosity short`
- Environment: `PYTEST_VIGIL__REPORT_VERBOSITY=short`

### Global Session Timeout

Set a maximum duration for the entire test run. If the total execution time exceeds this limit, pytest-vigil will automatically terminate the test run.

```bash
# Terminate if test run exceeds 15 minutes
pytest --vigil-session-timeout 900
```

**Termination Behavior:**
1. **Graceful Termination**: Upon timeout, pytest-vigil sends `SIGTERM` (or `SIGINT` on systems without `SIGTERM`) to allow ongoing tests to complete and clean up resources.
2. **Grace Period**: Waits some time (configurable via `PYTEST_VIGIL__SESSION_TIMEOUT_GRACE_PERIOD`) for graceful shutdown.
3. **Forceful Termination**: If the process doesn't terminate within the grace period, pytest-vigil sends `SIGKILL` to forcefully stop the test run.

**CI Environment**: Like per-test limits, session timeout is automatically multiplied by the CI multiplier (default `2x`) when running in CI environments.

**Configuration**:
- CLI: `--vigil-session-timeout 900 --vigil-session-timeout-grace-period 10`
- Environment: `PYTEST_VIGIL__SESSION_TIMEOUT=900.0`
- Grace period environment: `PYTEST_VIGIL__SESSION_TIMEOUT_GRACE_PERIOD=5.0`

### Markers

Apply limits to specific tests. All arguments are optional.

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
def test_critical_path():
    ...
```

### Configuration (Env)

Configure via environment variables (prefix `PYTEST_VIGIL__`):

- `PYTEST_VIGIL__TIMEOUT=5.0`
- `PYTEST_VIGIL__CI_MULTIPLIER=2.0`
- `PYTEST_VIGIL__STALL_TIMEOUT=10.0`
- `PYTEST_VIGIL__SESSION_TIMEOUT=900.0`
- `PYTEST_VIGIL__SESSION_TIMEOUT_GRACE_PERIOD=5.0`
- `PYTEST_VIGIL__REPORT_VERBOSITY=short`  # Options: none, short, full
