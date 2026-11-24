"""Regression tests for fixture cleanup after per-test timeouts."""

import signal

import pytest

pytest_plugins = ["pytester"]
pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGALRM"), reason="Requires SIGALRM"
)


@pytest.mark.parametrize("workers", [0, 1])
@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
def test_timeout_preserves_fixture_cleanup(pytester, monkeypatch, workers, phase):
    """Timeouts must preserve remaining finalizers and allow slow cleanup to finish."""
    monkeypatch.setenv("PYTEST_VIGIL__CI_MULTIPLIER", "1")
    marker = pytester.path / "cleanup.txt"
    pytester.makepyfile(f"""
        import time
        from pathlib import Path
        import pytest

        def record(event):
            with Path({str(marker)!r}).open("a") as stream:
                stream.write(event + "\\n")

        @pytest.fixture
        def outer():
            yield
            record("outer")

        @pytest.fixture
        def resource(outer):
            yield
            # Cross the original kernel-alarm deadline during cleanup.
            time.sleep(1.2)
            record("resource")

        @pytest.fixture
        def subject(resource):
            if {phase!r} == "setup":
                time.sleep(5)
            yield
            if {phase!r} == "teardown":
                time.sleep(5)

        @pytest.mark.vigil(timeout=0.3)
        def test_timeout(subject):
            if {phase!r} == "call":
                time.sleep(5)

        def test_afterwards():
            assert Path({str(marker)!r}).read_text().splitlines() == ["resource", "outer"]
    """)
    args = ["-n", "1"] if workers else []
    result = pytester.runpytest_subprocess(*args, timeout=30)
    if phase == "call":
        result.assert_outcomes(failed=1, passed=1)
    elif phase == "setup":
        result.assert_outcomes(errors=1, passed=1)
    else:
        result.assert_outcomes(errors=1, passed=2)
    assert marker.read_text().splitlines() == ["resource", "outer"]
    assert "INTERNALERROR>" not in result.stdout.str() + result.stderr.str()


@pytest.mark.parametrize("workers", [0, 1])
def test_each_retry_cleans_up_and_rearms_timeout(pytester, monkeypatch, workers):
    """Every timed-out attempt cleans up, then the next attempt times out too."""
    monkeypatch.setenv("PYTEST_VIGIL__CI_MULTIPLIER", "1")
    marker = pytester.path / "attempts.txt"
    pytester.makepyfile(f"""
        import time
        from pathlib import Path
        import pytest

        def record(event):
            with Path({str(marker)!r}).open("a") as stream:
                stream.write(event + "\\n")

        @pytest.fixture
        def resource():
            record("setup")
            yield
            time.sleep(1.2)
            record("cleanup")

        @pytest.mark.vigil(timeout=0.3, retry=1)
        def test_timeout(resource):
            try:
                time.sleep(5)
            except Exception:
                record("swallowed")
            record("completed")
    """)
    args = ["-n", "1"] if workers else []
    result = pytester.runpytest_subprocess(*args, timeout=30)
    result.assert_outcomes(failed=1)
    assert marker.read_text().splitlines() == ["setup", "cleanup", "setup", "cleanup"]
    assert "INTERNALERROR>" not in result.stdout.str() + result.stderr.str()
