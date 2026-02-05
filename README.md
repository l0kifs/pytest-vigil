<div align="center">

![pytest-vigil](https://socialify.git.ci/l0kifs/pytest-vigil/image?description=1&font=Inter&language=1&name=1&owner=1&pattern=Signal&theme=Light)

# Pytest Vigil - Reliability Vigilance for Pytest

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
![GitHub last commit](https://img.shields.io/github/last-commit/l0kifs/pytest-vigil)
![GitHub Release Date](https://img.shields.io/github/release-date/l0kifs/pytest-vigil?label=last%20release)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pytest-vigil?label=pypi%20downloads)
![GitHub repo size](https://img.shields.io/github/repo-size/l0kifs/pytest-vigil)



</div>

## Features

- **Resource Enforcement**: Set hard limits on **Time**, **Memory** (MB), and **CPU** (%).
- **Stall Detection**: Detects deadlocks by monitoring low CPU usage over time.
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
| `--vigil-report` | - | No | `None` | Path to JSON report file |

```bash
pytest --vigil-timeout 5 --vigil-memory 512 --vigil-cpu 80
```

### Markers

Apply limits to specific tests. All arguments are optional.

| Parameter | Type | Unit | Default | Description |
|-----------|------|------|---------|-------------|
| `timeout` | `float` | `s` | `None` | Test timeout |
| `memory` | `float` | `MB` | `None` | Memory limit |
| `cpu` | `float` | `%` | `None` | CPU limit |
| `retry` | `int` | - | `0` | Number of retries on failure |
| `stall_timeout` | `float` | `s` | `None` | Max duration of low CPU activity |
| `stall_cpu_threshold`| `float` | `%` | `0.1` | CPU threshold for stall detection |

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
