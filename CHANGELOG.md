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

## [0.8.0] - 2026-04-07

### Changed
- Replaced `loguru` with stdlib `logging` throughout the codebase. The plugin now uses a thin `_KeywordAdapter` wrapper (`infrastructure/observability/logging.py`) that preserves `log.info("msg", key=value)` call-site ergonomics while routing through the standard library. Host applications can configure, filter, and route plugin logs using any normal Python logging setup.
- `loguru>=0.7.0` removed from runtime dependencies. The plugin now has one fewer third-party dependency.
- Package root installs a `NullHandler` on the `pytest_vigil` logger namespace so the plugin stays silent by default until the host configures a handler.

### Added
- `src/pytest_vigil/infrastructure/observability/logging.py` — stdlib `logging` adapter (`get_logger`, `_KeywordAdapter`, `bind`) that converts keyword call arguments into `extra` fields.
- `docs/ddd-architecture-rules.md` — architecture rules for DDD-based Python projects.
- `docs/logging-rules.md` updated to be plugin-independent (removed `pytest-beacon` specific references).

## [0.7.2] - 2026-03-13

### Fixed
- `VigilMonitor.stop()` now wraps `thread.join()` in `try/except BaseException` to handle a SIGALRM race condition: a signal already placed in the OS pending-signal set before `cancel_alarm()` ran could fire during `lock.acquire()` inside `thread.join()`, raising `TimeoutException` in cleanup code and crashing xdist workers with `INTERNALERROR`.

## [0.7.1] - 2026-03-11

### Fixed
- `TimeoutException` (a `BaseException` subclass) now correctly caught per retry attempt in `pytest_runtest_protocol`, preventing the xdist worker crash that produced `INTERNALERROR> RuntimeError: Unexpectedly no active workers available`.
- Existing xdist timeout test updated: replaced `"TimeoutException: ..." in output` assertion (only matched the old crash traceback) with `assert_outcomes(passed=1, failed=1)` and `"INTERNALERROR>" not in output` checks that correctly describe the fixed behaviour.

### Tests
- Added `TestTimeoutExceptionXdistWorkerSafety` class in `tests/resource_limits/test_resource_limits_xdist.py` with 5 targeted regression tests covering: single timeout, back-to-back timeouts in one worker, timeout across retry attempts, timeout followed by passing test, and exit-code verification.
- Added `TestRetryWithTimeoutXdist` class in `tests/retry_mechanism/test_retry_xdist.py` with 3 tests covering: all retry attempts timing out, timeout on first attempt then passing on retry, and worker liveness after exhausted retried timeout.

## [0.7.0] - 2026-03-04

### Added
- **Per-test timeout reliability — layered enforcement** (`docs/feature-per-test-timeout.md`):
  - **Layer 2 — Kernel alarm backstop** (Unix, automatic): `signal.alarm()` is armed at test start when a timeout is configured. Fires independently of the monitoring thread, ensuring the test is interrupted even if the thread is delayed or dead.
  - **Layer 3 — Faulthandler diagnostics** (automatic when timeout is set): `faulthandler.dump_traceback_later()` is armed at `timeout + 1 s`. Writes C-level thread tracebacks directly to stderr (bypassing pytest capture), surviving even when Python is blocked inside a C extension.
  - **Layer 4 — Force-exit escalation** (opt-in): New `--vigil-force-exit-delay` CLI option and `PYTEST_VIGIL__FORCE_EXIT_DELAY` env var. When set, calls `os._exit(124)` if the soft interrupt is not handled within the specified delay. Useful for tests permanently stuck in GIL-holding C extensions.
- New test suite `tests/timeout_reliability/` covering all four reliability layers:
  - `test_signal_alarm_backstop.py` — kernel alarm set/cancel/reset-between-retries
  - `test_faulthandler_diagnostics.py` — faulthandler armed/cancelled/output-on-hang
  - `test_force_exit_escalation.py` — escalation fires / is cancelled on clean exit
  - `test_monitor_stop_responsiveness.py` — monitor stops promptly (Event.wait fix)
  - `test_interrupt_reliability_xdist.py` — xdist worker isolation sanity checks

### Changed
- `VigilMonitor` now uses `threading.Event.wait(interval)` instead of `time.sleep(interval)` so the monitor thread stops immediately when signalled rather than waiting out the full sleep interval.
- `Interrupter` refactored to accept `force_exit_delay` parameter and manage the escalation thread lifecycle.
- `SignalManager` gained `set_alarm(timeout)` and `cancel_alarm()` methods; `restore()` now also cancels any pending alarm before reinstating the previous handler.

## [0.6.2] - 2026-02-26

### Added
- Added a regression test to verify `pytest --help` renders pytest-vigil CLI options.

### Fixed
- Escaped percent signs in CLI help text for CPU-related options to prevent help rendering issues.

## [0.6.1] - 2026-02-19

### Changed
- JSON reporting configuration and naming were clarified for consistency:
  - Renamed settings `report_verbosity` → `console_report_verbosity`
  - Renamed settings `report_filename` → `json_report_filename`
  - Renamed settings `vigil_json_report` → `json_report`
  - Renamed CLI option `--vigil-report` → `--vigil-json-report`
- Relative JSON report output continues to default under `.pytest_vigil`

### Fixed
- Updated tests and documentation to match the new reporting names and options

## [0.6.0] - 2026-02-19

### Changed
- Refactored internal architecture to comply with Domain-Driven Design (DDD) principles
- Moved pytest plugin entry point from `pytest_vigil.plugin` to `pytest_vigil.entry_points.plugin`
- Extracted CLI terminal reporting into `infrastructure/reporting/cli_reporter.py` (`CliReporter`)
- Extracted JSON report writing into `infrastructure/reporting/json_reporter.py` (`JsonReporter`)
- All `__init__.py` files now contain only docstrings (no imports or code)
- Development status updated to **Production/Stable**

### Added
- `ExecutionResult` domain model in `domains/reliability/models.py` for typed, immutable per-test execution records
- `infrastructure/reporting/` sub-package for reporting infrastructure

### Fixed
- CLI short report labels no longer contain extra padding spaces (e.g. `Total Tests: 6` instead of `Total Tests:      6`)

## [0.5.1] - 2026-02-07

### Fixed
- Session timeout now displays last executed test when timeout occurs between tests (instead of showing no test information)
- Added tracking of last executed test nodeid for better session timeout reporting
- Session timeout message now clearly indicates "(Timeout occurred between tests)" when applicable

### Added
- New test case `test_session_timeout_between_tests_shows_last_test` to verify correct behavior when timeout occurs between tests

## [0.5.0] - 2026-02-06

### Added
- CLI report verbosity control via `--vigil-cli-report-verbosity` option with three levels:
  - `none`: No reliability report displayed (useful for CI pipelines)
  - `short`: Summary statistics only (default) - shows total tests, averages, fastest/slowest tests, resource stats
  - `full`: Detailed table with all tests and their individual metrics
- Environment variable support for report verbosity: `PYTEST_VIGIL__REPORT_VERBOSITY`
- Comprehensive test suite for CLI report functionality (test_cli_report.py)
- Summary statistics in short report mode: average duration, fastest/slowest tests, peak CPU/memory usage

### Changed
- Default terminal report now shows summary statistics instead of full detailed table for better readability
- Documentation updated with CLI report verbosity usage examples and configuration options

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

[Unreleased]: https://github.com/l0kifs/pytest-vigil/compare/v0.8.0...HEAD
[0.8.0]: https://github.com/l0kifs/pytest-vigil/compare/v0.7.2...v0.8.0
[0.7.2]: https://github.com/l0kifs/pytest-vigil/compare/v0.7.1...v0.7.2
[0.6.2]: https://github.com/l0kifs/pytest-vigil/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/l0kifs/pytest-vigil/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/l0kifs/pytest-vigil/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/l0kifs/pytest-vigil/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/l0kifs/pytest-vigil/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/l0kifs/pytest-vigil/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/l0kifs/pytest-vigil/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/l0kifs/pytest-vigil/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/l0kifs/pytest-vigil/releases/tag/v0.1.0
