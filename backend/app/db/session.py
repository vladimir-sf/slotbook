"""Synchronous PostgreSQL 16 transactions (T009), with no import-time connection.

Construct one engine per process using private DATABASE_URL configuration, then
share the Database factory, never a Session. Enter AND leave transaction() in
the same worker thread; each invocation owns a new session/transaction. Pass that
session to DatabaseClock for fresh wall-clock samples after waits (T018).

This module neither migrates nor retries. A commit error/unknown acknowledgement
must propagate: it does not prove rollback. Callers must not commit inside a scope.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, URL, make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker


class DatabaseConfigurationError(RuntimeError):
    """Safe configuration/preflight failure; contains no URL or server diagnostics."""


def database_url(value: str | URL | None = None) -> URL:
    """Require explicit PostgreSQL configuration and the locked sync psycopg driver."""
    try:
        url = make_url(value if value is not None else os.environ.get("DATABASE_URL", ""))
    except (ArgumentError, TypeError, ValueError):
        raise DatabaseConfigurationError("database_url_invalid") from None
    if (
        url.drivername not in ("postgresql", "postgresql+psycopg")
        or not url.database
        or not url.username
    ):
        raise DatabaseConfigurationError("database_url_invalid")
    return url.set(drivername="postgresql+psycopg")


def create_database_engine(value: str | URL | None = None) -> Engine:
    return create_engine(
        database_url(value),
        isolation_level="READ COMMITTED",
        connect_args={"options": "-c timezone=UTC", "connect_timeout": 5},
        pool_pre_ping=True,
        echo=False,
        hide_parameters=True,
    )


def verify_database(connection: Connection) -> None:
    """Fail closed on unsupported version, weakened commit settings or session drift.

    Checks current transaction settings, not just server defaults. This cannot
    prove storage/hosting durability, and must not be presented as RP-01–17 proof.
    """
    if connection.dialect.name != "postgresql":
        raise DatabaseConfigurationError("database_postgresql_required")
    try:
        settings = connection.execute(
            text(
                "SELECT current_setting('server_version_num')::integer, "
                "current_setting('fsync'), current_setting('synchronous_commit'), "
                "current_setting('TimeZone'), current_setting('transaction_isolation')"
            )
        ).one()
    except SQLAlchemyError:
        raise DatabaseConfigurationError("database_preflight_unavailable") from None
    version, fsync, synchronous_commit, timezone, isolation = settings
    if not isinstance(version, int) or not 160000 <= version < 170000:
        raise DatabaseConfigurationError("database_postgresql_16_required")
    if fsync != "on" or synchronous_commit != "on":
        raise DatabaseConfigurationError("database_durability_required")
    if timezone != "UTC" or isolation != "read committed":
        raise DatabaseConfigurationError("database_session_settings_invalid")


class Database:
    """Engine/sessionmaker may be shared by threads; sessions may not.

    Keep the context inside a single synchronous operation. It commits on normal
    exit, rolls back on failure, and closes even when preflight or COMMIT fails.
    No global/scoped/thread-local session or async adapter is provided.
    """

    def __init__(self, engine: Engine) -> None:
        if engine.dialect.name != "postgresql":
            raise DatabaseConfigurationError("database_postgresql_required")
        self._sessions = sessionmaker(bind=engine, autobegin=False, expire_on_commit=True)

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        with self._sessions() as session, session.begin():
            connection = session.connection()
            # Reset timezone on every scope, including a reused pooled connection.
            connection.execute(text("SET LOCAL TIME ZONE 'UTC'"))
            verify_database(connection)
            yield session
