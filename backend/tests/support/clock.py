"""Explicitly injected controlled time; never a substitute for DB clock_timestamp()."""

from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Protocol


class Clock(Protocol):
    """Shared callable dependency for future test server/worker factories."""

    def now(self) -> datetime:
        """Return an aware UTC instant."""
        ...


class FrozenClock:
    """Thread-safe fixture clock. set() may deliberately rewind a boundary case."""

    def __init__(self, instant: datetime) -> None:
        self._lock = Lock()
        self._instant = self._utc(instant)

    @staticmethod
    def _utc(instant: datetime) -> datetime:
        if instant.utcoffset() is None:
            raise ValueError("fixture_clock_requires_aware_instant")
        return instant.astimezone(UTC)

    def now(self) -> datetime:
        with self._lock:
            return self._instant

    def set(self, instant: datetime) -> None:
        normalized = self._utc(instant)
        with self._lock:
            self._instant = normalized

    def advance(self, delta: timedelta) -> None:
        if delta < timedelta(0):
            raise ValueError("fixture_clock_requires_nonnegative_delta")
        with self._lock:
            self._instant += delta
