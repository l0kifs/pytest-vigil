All tests for one functionality should be in one dedicated test directory under `tests`.
If there are tests for this functionality in other test files, they should be moved to the dedicated test directory.

Tests should cover:
- Proper functioning of functionality with all types of test outcomes (pass, fail, skip, xfail, xpass).
- All available parameters for this functionality.
- Interaction of functionality with CI environment.
- Proper functioning with xdist enabled.
- Generation of appropriate reports if needed.
- Analyze and cover possible edge cases.
- Ensure no interference with other pytest-vigil features.