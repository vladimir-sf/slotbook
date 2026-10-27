"""Authoritative clock injection and elapsed UTC/pinned IANA primitives (T018).

Call DatabaseClock.now() AFTER every relevant wait, inside the caller's current
connection/transaction. A clock sample is neither admission nor proof of COMMIT.
This module never reads private test controls or falls back to a host clock.
"""

import os
import re
import zoneinfo
from datetime import UTC, datetime, timedelta
from importlib import import_module, metadata, resources
from pathlib import Path
from typing import Protocol

from sqlalchemy import DateTime, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class Clock(Protocol):
    def now(self) -> datetime:
        """Return a freshly sampled aware UTC instant."""
        ...


class DatabaseClockError(RuntimeError):
    """Unavailable or invalid authoritative time; never substitute host time."""


class TimezoneDataError(RuntimeError):
    """Invalid configuration or missing/mismatched packaged timezone data."""


def as_utc(instant: datetime) -> datetime:
    if instant.utcoffset() is None:
        raise ValueError("aware_instant_required")
    return instant.astimezone(UTC)


def elapsed_after(anchor: datetime, elapsed: timedelta) -> datetime:
    """Add elapsed time rather than IANA wall-calendar time."""
    return as_utc(anchor) + elapsed


def deadline_reached(now: datetime, deadline: datetime) -> bool:
    """Equality expires; normalize before comparing even when both zones match."""
    return as_utc(now) >= as_utc(deadline)


class DatabaseClock:
    """Use an injected SQLAlchemy Connection/Session; no cached/transaction time.

    The caller owns transaction scope and invokes now() again after lock waits.
    This adapter does not acquire locks, commit, retry or consult configuration.
    """

    def __init__(self, connection: Connection | Session) -> None:
        self._connection = connection

    def now(self) -> datetime:
        try:
            value: object = self._connection.execute(
                select(func.clock_timestamp(type_=DateTime(timezone=True)))
            ).scalar_one()
        except SQLAlchemyError:
            raise DatabaseClockError("database_clock_unavailable") from None
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise DatabaseClockError("database_clock_invalid_instant")
        return as_utc(value)


def timezone_versions() -> dict[str, str]:
    """Validate empty PYTHONTZPATH, UTC and the exact lock/package/IANA source.

    Import is side-effect free; startup/factories explicitly invoke this check.
    Never hide an invalid environment by resetting paths or using system tzdata.
    """
    if os.environ.get("PYTHONTZPATH") != "" or zoneinfo.TZPATH or os.environ.get("TZ") != "UTC":
        raise TimezoneDataError("timezone_configuration_invalid")
    try:
        package = import_module("tzdata")
        version = metadata.version("tzdata")
        lock = Path(__file__).resolve().parents[1] / "requirements.lock"
        pins = re.findall(r"(?m)^tzdata==([^\s\\]+)", lock.read_text())
        iana = getattr(package, "IANA_VERSION", None)
        if (
            pins != [version]
            or getattr(package, "__version__", None) != version
            or not isinstance(iana, str)
            or not iana
        ):
            raise TimezoneDataError("timezone_data_version_invalid")
        with resources.files("tzdata.zoneinfo").joinpath("UTC").open("rb") as source:
            zoneinfo.ZoneInfo.from_file(source, key="UTC")
    except (ImportError, OSError, ValueError):
        raise TimezoneDataError("timezone_data_unavailable") from None
    return {"tzdata": version, "iana": iana, "timezone_source": "tzdata"}


def load_timezone(name: str) -> zoneinfo.ZoneInfo:
    """Read only the locked package, bypassing both host paths and ZoneInfo cache."""
    timezone_versions()
    parts = name.split("/")
    if any(part in ("", ".", "..") or "\\" in part for part in parts):
        raise ValueError("invalid_timezone")
    try:
        with resources.files("tzdata.zoneinfo").joinpath(*parts).open("rb") as source:
            return zoneinfo.ZoneInfo.from_file(source, key=name)
    except (OSError, ValueError):
        raise ValueError("invalid_timezone") from None


def to_local(instant: datetime, timezone: str) -> datetime:
    return as_utc(instant).astimezone(load_timezone(timezone))


def local_instants(local: datetime, timezone: str) -> tuple[datetime, ...]:
    """UTC preimages of one naive wall label: zero, one or two; never shift gaps.

    Round-trip both folds and deduplicate in UTC, not by wall-label equality.
    Window construction and slot eligibility remain separate later tasks.
    """
    if local.tzinfo is not None:
        raise ValueError("local_label_must_be_naive")
    zone = load_timezone(timezone)
    instants: set[datetime] = set()
    for fold in (0, 1):
        candidate = local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if candidate.astimezone(zone).replace(tzinfo=None, fold=0) == local.replace(fold=0):
            instants.add(candidate)
    return tuple(sorted(instants))
