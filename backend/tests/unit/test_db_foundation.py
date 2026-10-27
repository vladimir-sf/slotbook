"""T009 regression checks; real PostgreSQL acceptance is run separately.

No SQLite stand-in and no later entity/constraint suite (T010). All inputs are
synthetic; exceptions are checked for safe codes without printing private data.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import MagicMock, Mock

import pytest
from alembic import command
from alembic.config import Config
from alembic.util import CommandError
from sqlalchemy import Column, Integer, Table, UniqueConstraint
from sqlalchemy.engine import Connection, Engine, URL
from sqlalchemy.exc import OperationalError

from app.db import session as db
from app.db.base import Base
from app.models import Base as RegisteredBase

pytestmark = pytest.mark.unit
BACKEND = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "value",
    [
        "",
        "invalid",
        "sqlite://",
        "postgresql+asyncpg://synthetic/db",
        "postgresql:///db",
        "postgresql://synthetic@localhost",
    ],
    ids=lambda _: "invalid-config",
)
def test_invalid_configuration_is_rejected_without_echoing_it(value):
    with pytest.raises(db.DatabaseConfigurationError) as error:
        db.database_url(value)
    assert str(error.value) == "database_url_invalid"
    assert error.value.__suppress_context__ or error.value.__context__ is None


def test_url_uses_only_explicit_configuration_and_locked_driver(monkeypatch):
    value = URL.create("postgresql", username="synthetic", host="db", database="foundation")
    monkeypatch.setenv("DATABASE_URL", value.render_as_string(hide_password=False))
    assert db.database_url() == value.set(drivername="postgresql+psycopg")
    assert db.database_url(value) == db.database_url()
    monkeypatch.delenv("DATABASE_URL")
    with pytest.raises(db.DatabaseConfigurationError, match="database_url_invalid"):
        db.database_url()


def test_engine_has_read_committed_utc_and_no_sql_logging(monkeypatch):
    create = Mock()
    monkeypatch.setattr(db, "create_engine", create)
    db.create_database_engine("postgresql://synthetic@db/foundation")
    options = create.call_args.kwargs
    assert options == {
        "isolation_level": "READ COMMITTED",
        "connect_args": {"options": "-c timezone=UTC", "connect_timeout": 5},
        "pool_pre_ping": True,
        "echo": False,
        "hide_parameters": True,
    }


def connection(settings=(160015, "on", "on", "UTC", "read committed")):
    result = Mock(spec=Connection)
    result.dialect = Mock(name="dialect")
    result.dialect.name = "postgresql"
    result.execute.return_value.one.return_value = settings
    return result


def test_preflight_reads_current_settings():
    target = connection()
    db.verify_database(target)
    sql = str(target.execute.call_args.args[0])
    for setting in (
        "server_version_num",
        "fsync",
        "synchronous_commit",
        "TimeZone",
        "transaction_isolation",
    ):
        assert f"current_setting('{setting}')" in sql


@pytest.mark.parametrize("version", [150000, 170000, None, "160015"])
def test_preflight_rejects_other_postgresql_versions(version):
    with pytest.raises(db.DatabaseConfigurationError, match="database_postgresql_16_required"):
        db.verify_database(connection((version, "on", "on", "UTC", "read committed")))


@pytest.mark.parametrize(
    "fsync,commit",
    [("off", "on"), ("on", "off"), ("on", "local"), ("on", "remote_write"), ("on", "remote_apply")],
)
def test_preflight_rejects_weakened_or_unapproved_commit_settings(fsync, commit):
    with pytest.raises(db.DatabaseConfigurationError, match="database_durability_required"):
        db.verify_database(connection((160015, fsync, commit, "UTC", "read committed")))


@pytest.mark.parametrize(
    "zone,isolation",
    [("Europe/Vienna", "read committed"), ("UTC", "repeatable read"), ("UTC", "serializable")],
)
def test_preflight_rejects_session_drift(zone, isolation):
    with pytest.raises(db.DatabaseConfigurationError, match="database_session_settings_invalid"):
        db.verify_database(connection((160015, "on", "on", zone, isolation)))


def test_preflight_masks_driver_diagnostics():
    target = connection()
    target.execute.side_effect = OperationalError("synthetic-statement", {}, Exception("synthetic"))
    with pytest.raises(db.DatabaseConfigurationError) as error:
        db.verify_database(target)
    assert str(error.value) == "database_preflight_unavailable"
    assert error.value.__suppress_context__


def test_non_postgresql_engines_and_connections_are_rejected():
    target = connection()
    target.dialect.name = "sqlite"
    for action in (lambda: db.verify_database(target), lambda: db.Database(target)):
        with pytest.raises(db.DatabaseConfigurationError, match="database_postgresql_required"):
            action()
    target.execute.assert_not_called()


def test_each_scope_owns_a_session_in_its_thread_and_closes_it(monkeypatch):
    sessions = []
    barrier = Barrier(2)

    def new_session():
        result = Mock()
        result.__enter__ = Mock(return_value=result)
        result.__exit__ = Mock(return_value=False)
        result.begin.return_value.__enter__ = Mock()
        result.begin.return_value.__exit__ = Mock(return_value=False)
        result.connection.return_value = connection()
        sessions.append(result)
        return result

    factory = Mock(return_value=new_session)
    monkeypatch.setattr(db, "sessionmaker", factory)
    engine = Mock(spec=Engine)
    engine.dialect = Mock()
    engine.dialect.name = "postgresql"
    database = db.Database(engine)

    def use():
        with database.transaction() as session:
            barrier.wait(timeout=5)
            return session

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(use) for _ in range(2)]
        values = [future.result(timeout=10) for future in futures]
    assert values[0] is not values[1]
    factory.assert_called_once_with(bind=engine, autobegin=False, expire_on_commit=True)
    for session in sessions:
        session.__exit__.assert_called_once_with(None, None, None)
        session.begin.return_value.__exit__.assert_called_once_with(None, None, None)
        assert str(session.connection.return_value.execute.call_args_list[0].args[0]) == (
            "SET LOCAL TIME ZONE 'UTC'"
        )


def test_base_registry_is_empty_and_has_stable_constraint_names():
    assert RegisteredBase is Base
    assert not Base.metadata.tables
    # Use a separate copy so the production registry remains empty.
    metadata = type(Base.metadata)(naming_convention=Base.metadata.naming_convention)
    table = Table(
        "synthetic", metadata, Column("id", Integer, primary_key=True), UniqueConstraint("id")
    )
    assert table.primary_key.name == "pk_synthetic"
    assert any(constraint.name == "uq_synthetic_id" for constraint in table.constraints)


@pytest.mark.parametrize("failure_phase", ["preflight", "body", "commit"])
def test_scope_closes_and_propagates_failure_without_retry(monkeypatch, failure_phase):
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = False
    transaction = session.begin.return_value
    transaction.__exit__.return_value = False
    session.connection.return_value = connection()
    failure = RuntimeError("synthetic_transaction_failure")
    preflight = Mock(side_effect=failure if failure_phase == "preflight" else None)
    monkeypatch.setattr(db, "verify_database", preflight)
    factory = Mock(return_value=session)
    monkeypatch.setattr(db, "sessionmaker", Mock(return_value=factory))
    engine = Mock(spec=Engine)
    engine.dialect = Mock()
    engine.dialect.name = "postgresql"
    if failure_phase == "commit":
        transaction.__exit__.side_effect = failure
    with pytest.raises(RuntimeError) as error, db.Database(engine).transaction():
        if failure_phase == "body":
            raise failure
    assert error.value is failure
    factory.assert_called_once()
    session.__exit__.assert_called_once()
    transaction.__exit__.assert_called_once()


@pytest.mark.parametrize("offline", [False, True])
def test_migration_cli_requires_private_online_configuration(monkeypatch, offline):
    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
    # Runtime credentials must never be used for migrations, even if configured.
    monkeypatch.setenv("DATABASE_URL", "postgresql://synthetic@localhost/foundation")
    config = Config(str(BACKEND / "alembic.ini"))
    code = "database_online_verification_required" if offline else "database_url_invalid"
    with pytest.raises(CommandError, match=code):
        command.upgrade(config, "head", sql=offline)
