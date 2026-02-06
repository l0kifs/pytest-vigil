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

## [0.4.0] - 2026-02-06

### Changed
- Default stall CPU threshold increased from 0.1% to 1.0% for more reliable detection
- Improved stall detection logic to use time-window-based measurement instead of single-point CPU check
- Enhanced session timeout implementation with better child process cleanup (including xdist workers)
- Session timeout now shows currently executing test in timeout message
- Session timeout exits with code 124 (GNU timeout convention)
- Improved session timeout cleanup to prevent resource leaks (semaphore leaks fixed)
- Session monitor now tracks current test nodeid for better timeout reporting

### Removed
- Consolidated test files: removed test_ci_multiplier.py, test_config.py, test_integration_xdist.py, test_markers.py
- Tests merged into comprehensive test suites: test_resource_limits.py, test_retry_mechanism.py, test_stall_detection.py, test_json_report.py, test_session_timeout.py

### Fixed
- Session timeout now properly terminates child processes including pytest-xdist workers
- Stall detection now correctly evaluates CPU activity over time window instead of instantaneous measurement
- Session timeout no longer leaves resource tracker warnings about leaked semaphores

## [0.3.0] - 2026-02-06

### Added
- Global session timeout feature with `--vigil-session-timeout` CLI option
- Configurable grace period for session timeout with `--vigil-session-timeout-grace-period` CLI option
- SessionMonitor class with graceful (SIGTERM) and forceful (SIGKILL) termination
- CI multiplier support for session timeout (automatically scales in CI environments)
- Environment variable configuration for session timeout (`PYTEST_VIGIL__SESSION_TIMEOUT`)
- Environment variable configuration for grace period (`PYTEST_VIGIL__SESSION_TIMEOUT_GRACE_PERIOD`)
- Comprehensive test suite for session timeout (20 tests covering all scenarios)
- Session timeout cleanup in pytest_sessionfinish hook
- Integration with existing features (xdist, retries, stall detection, resource limits)

### Changed
- Updated README with Global Session Timeout section and usage examples
- Enhanced CLI options table with session timeout parameters

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

[Unreleased]: https://github.com/l0kifs/pytest-vigil/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/l0kifs/pytest-vigil/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/l0kifs/pytest-vigil/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/l0kifs/pytest-vigil/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/l0kifs/pytest-vigil/releases/tag/v0.1.0
