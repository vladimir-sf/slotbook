"""Explicitly injected controlled time; never a substitute for DB clock_timestamp()."""

import json
import os
import re
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Protocol, Self


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


class FileClock:
    """Explicit test-entrypoint injection, never discovered from environment.

    Use as a context manager. The mode-0700 current-user directory is pinned by
    descriptor, and each sample reads its mode-0600 regular clock.json afresh.
    The host atomically replaces that file with exactly caseId and instant.
    These are controlled-time fixtures, not DB durability/concurrency evidence.
    """

    def __init__(self, directory: Path, *, case_id: str) -> None:
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", case_id) is None:
            raise ValueError("fixture_clock_control_invalid")
        self._case_id = case_id
        self._lock = Lock()
        self._directory = -1
        descriptor = -1
        try:
            descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            info = os.fstat(descriptor)
            if stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.geteuid():
                os.close(descriptor)
                raise ValueError("fixture_clock_control_invalid")
            self._directory = descriptor
        except OSError:
            if descriptor != -1:
                os.close(descriptor)
            raise ValueError("fixture_clock_control_unavailable") from None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            if self._directory != -1:
                os.close(self._directory)
                self._directory = -1

    @staticmethod
    def _record(pairs: list[tuple[str, object]]) -> dict[str, object]:
        record = dict(pairs)
        if len(record) != len(pairs):
            raise ValueError("fixture_clock_control_invalid")
        return record

    def now(self) -> datetime:
        with self._lock:
            if self._directory == -1:
                raise RuntimeError("fixture_clock_control_closed")
            try:
                # Recheck permission changes, keep the original directory identity.
                parent = os.fstat(self._directory)
                if stat.S_IMODE(parent.st_mode) != 0o700 or parent.st_uid != os.geteuid():
                    raise ValueError("fixture_clock_control_invalid")
                descriptor = os.open(
                    "clock.json",
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=self._directory,
                )
                with os.fdopen(descriptor, "rb") as source:
                    info = os.fstat(source.fileno())
                    if (
                        not stat.S_ISREG(info.st_mode)
                        or stat.S_IMODE(info.st_mode) != 0o600
                        or info.st_uid != os.geteuid()
                        or info.st_nlink > 1
                        or info.st_size > 4096
                    ):
                        raise ValueError("fixture_clock_control_invalid")
                    data = source.read(4097)
                if len(data) > 4096:
                    raise ValueError("fixture_clock_control_invalid")
                record = json.loads(data, object_pairs_hook=self._record)
                if (
                    not isinstance(record, dict)
                    or set(record) != {"caseId", "instant"}
                    or record["caseId"] != self._case_id
                    or not isinstance(record["instant"], str)
                    or re.fullmatch(
                        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
                        r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
                        record["instant"],
                    )
                    is None
                ):
                    raise ValueError("fixture_clock_control_invalid")
                return FrozenClock._utc(datetime.fromisoformat(record["instant"]))
            except OSError:
                raise ValueError("fixture_clock_control_unavailable") from None
            except (ValueError, RecursionError, OverflowError):
                raise ValueError("fixture_clock_control_invalid") from None
