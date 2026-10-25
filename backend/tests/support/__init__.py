"""T002 fixture regressions, collected as doctests within the assigned support paths.

Controlled-time and callback tests do not prove PostgreSQL durability or RP-01–17.
Each function groups one independently collected fixture contract.
"""

import pytest

pytestmark = pytest.mark.unit


def clock_contract() -> None:
    """Normalize offsets, share explicit injections and reject invalid mutations.

    >>> from datetime import UTC, datetime, timedelta, timezone
    >>> from concurrent.futures import ThreadPoolExecutor
    >>> from tests.support.clock import FrozenClock
    >>> clock = getfixture("frozen_clock")
    >>> clock.set(datetime(2030, 1, 1, 2, tzinfo=timezone(timedelta(hours=2))))
    >>> clock.now() == datetime(2030, 1, 1, tzinfo=UTC) and clock.now().tzinfo is UTC
    True
    >>> server_clock = worker_clock = clock
    >>> clock.advance(timedelta(hours=24, microseconds=1))
    >>> server_clock.now() == worker_clock.now() == datetime(2030, 1, 2, microsecond=1, tzinfo=UTC)
    True
    >>> before = clock.now()
    >>> with pytest.raises(ValueError, match="fixture_clock_requires_aware_instant"):
    ...     clock.set(datetime(2030, 1, 1))
    >>> clock.now() == before
    True
    >>> with pytest.raises(ValueError, match="fixture_clock_requires_aware_instant"):
    ...     FrozenClock(datetime(2030, 1, 1))
    >>> with pytest.raises(ValueError, match="fixture_clock_requires_nonnegative_delta"):
    ...     clock.advance(timedelta(microseconds=-1))
    >>> clock.now() == before
    True
    >>> with ThreadPoolExecutor(max_workers=4) as executor:
    ...     step = timedelta(microseconds=1)
    ...     futures = [executor.submit(clock.advance, step) for _ in range(100)]
    ...     assert all(f.result(timeout=2) is None for f in futures)
    >>> clock.now() == before + timedelta(microseconds=100)
    True
    >>> clock.set(datetime.max.replace(tzinfo=UTC))
    >>> with pytest.raises(OverflowError):
    ...     clock.advance(timedelta(microseconds=1))
    >>> clock.now() == datetime.max.replace(tzinfo=UTC)
    True
    """


def fault_contract() -> None:
    """Only registered named callbacks execute; failures propagate unchanged.

    >>> from tests.support.faults import FaultPoint
    >>> faults = getfixture("faults")
    >>> seen = []
    >>> faults(FaultPoint.BEFORE_ADMISSION_COMMIT)
    >>> for point in FaultPoint:
    ...     faults.register(point, seen.append)
    ...     faults(point)
    >>> seen == list(FaultPoint)
    True
    >>> faults.clear()
    >>> faults(FaultPoint.BEFORE_ADMISSION_COMMIT)
    >>> seen == list(FaultPoint)
    True
    >>> def lose_ack(point):
    ...     raise ConnectionError("synthetic_ack_loss")
    >>> faults.register(FaultPoint.ADMISSION_COMMITTED_ACK_LOST, lose_ack)
    >>> with pytest.raises(ConnectionError, match="synthetic_ack_loss"):
    ...     faults(FaultPoint.ADMISSION_COMMITTED_ACK_LOST)
    >>> with pytest.raises(ValueError, match="fixture_fault_requires_named_boundary"):
    ...     faults.register("unapproved_boundary", seen.append)
    >>> with pytest.raises(ValueError, match="fixture_fault_requires_named_boundary"):
    ...     faults("unapproved_boundary")
    >>> with pytest.raises(TypeError, match="fixture_fault_requires_callback"):
    ...     faults.register(FaultPoint.BEFORE_RESPONSE, None)
    """


def barrier_contract() -> None:
    """A bounded real wait synchronizes threads without fabricating a commit.

    >>> from concurrent.futures import ThreadPoolExecutor
    >>> from tests.support.faults import FaultBarrier, FaultPoint
    >>> barrier = FaultBarrier(timeout=2)
    >>> with ThreadPoolExecutor(max_workers=1) as executor:
    ...     future = executor.submit(barrier, FaultPoint.AFTER_TENTATIVE_INSERT)
    ...     assert barrier.reached.wait(timeout=2), "fixture_barrier_not_reached"
    ...     assert not future.done(), "fixture_barrier_did_not_block"
    ...     barrier.release.set()
    ...     assert future.result(timeout=2) is None
    >>> for invalid in (0, -1, float("inf"), float("nan")):
    ...     with pytest.raises(ValueError, match="fixture_barrier_requires_positive_timeout"):
    ...         FaultBarrier(timeout=invalid)
    >>> with pytest.raises(TimeoutError, match="fixture_barrier_release_timeout"):
    ...     FaultBarrier(timeout=0.001)(FaultPoint.BEFORE_BOOKING_COMMIT)
    >>> with pytest.raises(ValueError, match="fixture_fault_requires_named_boundary"):
    ...     FaultBarrier()("unapproved_boundary")
    """


def subprocess_contract() -> None:
    r"""Isolate children, private output, packaged tzdata and bounded cleanup.

    >>> from stat import S_IMODE
    >>> runtime = getfixture("private_runtime_dir")
    >>> S_IMODE(runtime.stat().st_mode) == 0o700
    True
    >>> children = getfixture("python_subprocess")
    >>> monkeypatch = getfixture("monkeypatch")
    >>> monkeypatch.setenv("SLOTBOOK_TEST_CONTROL_DIR", "synthetic_control")
    >>> monkeypatch.setenv("SLOTBOOK_SYNTHETIC_SECRET", "synthetic_secret")
    >>> child = children.start('import os, sys, zoneinfo; assert sys.flags.isolated; '
    ...     'assert "SLOTBOOK_TEST_CONTROL_DIR" not in os.environ; '
    ...     'assert "SLOTBOOK_SYNTHETIC_SECRET" not in os.environ; '
    ...     'assert os.environ["TZ"] == "UTC"; '
    ...     'assert os.environ["PYTHONTZPATH"] == ""; '
    ...     'assert zoneinfo.TZPATH == (); '
    ...     'assert zoneinfo.ZoneInfo("Europe/Vienna").key == "Europe/Vienna"; '
    ...     'print("synthetic_output")')
    >>> child.wait(timeout=5)
    0
    >>> all(S_IMODE(path.stat().st_mode) == 0o600 for path in runtime.iterdir())
    True
    >>> (runtime / "child-0.stdout").read_text() == "synthetic_output\n"
    True
    >>> failed = children.start('raise RuntimeError("synthetic_private_error")')
    >>> failed.wait(timeout=5) != 0
    True
    >>> "synthetic_private_error" in (runtime / "child-1.stderr").read_text()
    True
    >>> running = children.start("import time; time.sleep(60)")
    >>> children.close()
    >>> running.poll() is not None
    True
    >>> children.close()
    >>> with pytest.raises(RuntimeError, match="fixture_subprocess_factory_closed"):
    ...     children.start("pass")
    """


def subprocess_termination_contract() -> None:
    """A self-launched child ignoring termination is killed and reaped.

    >>> import signal, time
    >>> children = getfixture("python_subprocess")
    >>> runtime = getfixture("private_runtime_dir")
    >>> child = children.start('import os, signal, time; '
    ...     'signal.signal(signal.SIGTERM, signal.SIG_IGN); '
    ...     'os.close(os.open("ready", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)); '
    ...     'time.sleep(60)')
    >>> deadline = time.monotonic() + 5
    >>> while not (runtime / "ready").exists() and time.monotonic() < deadline:
    ...     time.sleep(0.01)
    >>> assert (runtime / "ready").exists(), "fixture_child_not_ready"
    >>> children.close()
    >>> child.returncode == -signal.SIGKILL
    True
    """


def production_isolation_contract() -> None:
    """Ordinary imports expose no test adapters, routes or production switches.

    >>> from pathlib import Path
    >>> backend = Path(__file__).resolve().parents[2]
    >>> code = (f"import sys, os; sys.path.insert(0, {str(backend)!r}); "
    ...     "os.environ['SLOTBOOK_TEST_CONTROL_DIR'] = 'synthetic_control'; "
    ...     "from app.main import app; "
    ...     "assert not any(n.startswith('tests.support') for n in sys.modules); "
    ...     "assert {r.path for r in app.routes} == "
    ...     "{'/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc', '/health'}")
    >>> child = getfixture("python_subprocess").start(code)
    >>> assert child.wait(timeout=5) == 0, "fixture_production_import_isolation_failed"
    """
