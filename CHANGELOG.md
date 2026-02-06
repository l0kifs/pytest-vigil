# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- None yet

### Changed
- None yet

### Fixed
- None yet

## [0.2.0] - 2026-02-06

### Added
- CLI option `--vigil-stall-timeout` for global stall timeout configuration
- CLI option `--vigil-stall-cpu-threshold` for global stall CPU threshold configuration
- Comprehensive test coverage for new stall-related CLI options
- Tests validating proper override hierarchy (ENV → CLI → Marker) for stall parameters

### Changed
- Extended CLI configuration capabilities to include all stall detection parameters

## [0.1.0] - 2026-02-06

### Added
- Core pytest plugin with resource monitoring and enforcement capabilities
- Resource limits for timeout (seconds), memory (MB), and CPU (%)
- CLI options for setting global limits (`--vigil-timeout`, `--vigil-memory`, `--vigil-cpu`, `--vigil-retry`, `--vigil-report`)
- Marker support (`@pytest.mark.vigil`) for per-test resource configuration
- Stall detection to identify deadlocks via low CPU usage monitoring
- CI awareness with automatic limit scaling (configurable multiplier, default 2x)
- Retry mechanism for failed or resource-violating tests
- JSON report generation with detailed resource usage metrics and test outcomes
- Environment variable configuration with `PYTEST_VIGIL__` prefix
- Thread stack dumps on timeout/interrupt for debugging context
- Integration with pytest-xdist for parallel test execution
- Configurable monitoring intervals and thresholds via settings
- Comprehensive test suite covering all features including CI multiplier, retry logic, stall detection, and xdist integration

[Unreleased]: https://github.com/l0kifs/pytest-vigil/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/l0kifs/pytest-vigil/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/l0kifs/pytest-vigil/releases/tag/v0.1.0
