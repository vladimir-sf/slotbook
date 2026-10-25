"""Private Python callbacks only; no HTTP controls, process killing or mocked commits."""

from collections.abc import Callable
from enum import StrEnum
from math import isfinite
from threading import Event


class FaultPoint(StrEnum):
    """Distinct boundaries for later real-transaction tests, never receipt assertions."""

    BEFORE_ADMISSION_COMMIT = "before_admission_commit"
    ADMISSION_COMMITTED_ACK_LOST = "admission_committed_ack_lost"
    AFTER_TENTATIVE_INSERT = "after_tentative_insert"
    BEFORE_BOOKING_COMMIT = "before_booking_commit"
    BOOKING_COMMITTED_ACK_LOST = "booking_committed_ack_lost"
    BEFORE_RESPONSE = "before_response"


type FaultCallback = Callable[[FaultPoint], None]


class Faults:
    """Register before starting test threads; callback failures propagate unchanged."""

    def __init__(self) -> None:
        self._callbacks: dict[FaultPoint, FaultCallback] = {}

    def register(self, point: FaultPoint, callback: FaultCallback) -> None:
        if not isinstance(point, FaultPoint):
            raise ValueError("fixture_fault_requires_named_boundary")
        if not callable(callback):
            raise TypeError("fixture_fault_requires_callback")
        self._callbacks[point] = callback

    def clear(self) -> None:
        self._callbacks.clear()

    def __call__(self, point: FaultPoint) -> None:
        if not isinstance(point, FaultPoint):
            raise ValueError("fixture_fault_requires_named_boundary")
        callback = self._callbacks.get(point)
        if callback is not None:
            callback(point)


class FaultBarrier:
    """One-shot reached/release handshake for in-process transaction threads.

    Deadlines use real Event waits, independently of the injected fixture clock.
    Host control files, subprocess transaction adapters and test server/worker
    entrypoints belong to later tasks; this object performs no lifecycle actions.
    """

    def __init__(self, *, timeout: float = 5.0) -> None:
        if not isfinite(timeout) or timeout <= 0:
            raise ValueError("fixture_barrier_requires_positive_timeout")
        self.timeout = timeout
        self.reached = Event()
        self.release = Event()

    def __call__(self, point: FaultPoint) -> None:
        if not isinstance(point, FaultPoint):
            raise ValueError("fixture_fault_requires_named_boundary")
        self.reached.set()
        if not self.release.wait(timeout=self.timeout):
            raise TimeoutError("fixture_barrier_release_timeout")
