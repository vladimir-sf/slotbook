"""T010 real PostgreSQL fixtures and migration assertions, intentionally red.

Run only through an approved disposable host fixture. It supplies a mode-0600
SLOTBOOK_TEST_DATABASE_CONFIG file in a mode-0700 directory, containing version=1,
task=T010, run_id (12 hex digits), container_id, postgres_image_id and owner_url.
The host must verify its exact container labels/image/internal network first,
provision t010_owner/runtime/backup/outsider logins with private random passwords,
and create the control DB/comment described by read_config(). The owner_url's
password is shared by these synthetic logins only in this disposable fixture.

No Docker operations, shared database reset, SQLite fallback, skipped cases or
xfails. Each case creates/migrates/drops only its own uniquely named DB; a private
file lock serializes users of the same fixture. Logs never enter public evidence.
Missing mapped relations fail assertions in test bodies, not fixture setup.
"""

import fcntl
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from psycopg import sql
from sqlalchemy.engine import URL

from app.db.session import DatabaseConfigurationError, database_url

pytestmark = pytest.mark.integration
BACKEND = Path(__file__).resolve().parents[2]
PUBLIC_TABLES = ("activities", "weekly_windows", "blocked_dates", "bookings")
PRIVATE_TABLES = (
    "booking_contacts",
    "booking_attempts",
    "attempt_bindings",
    "retry_generation",
    "recovery_events",
    "worker_status",
    "admins",
    "admin_sessions",
)
HISTORY_COLUMNS = {"id", "activity_id", "starts_at", "ends_at", "status", "canceled_at"}


def connect(url: URL, *, autocommit: bool = False):
    """Always open an independent locked-driver PostgreSQL connection."""
    url = database_url(url)
    return psycopg.connect(
        host=url.host,
        port=url.port or 5432,
        dbname=url.database,
        user=url.username,
        password=url.password,
        sslmode="disable",
        connect_timeout=5,
        autocommit=autocommit,
        options="-c timezone=UTC -c default_transaction_isolation=read\\ committed "
        "-c statement_timeout=15000 -c lock_timeout=10000",
    )


@dataclass(repr=False)
class Target:
    run_id: str
    owner_url: URL = field(repr=False)

    @property
    def marker(self):
        return "slotbook:T010:" + self.run_id

    def url(self, database: str, role: str = "owner"):
        assert role in ("owner", "runtime", "backup", "outsider")
        return self.owner_url.set(database=database, username="t010_" + role)

    def verify_control(self, connection):
        row = connection.execute(
            "SELECT current_database(), current_user, "
            "current_setting('server_version_num')::int, current_setting('fsync'), "
            "current_setting('synchronous_commit'), "
            "shobj_description(oid, 'pg_database') FROM pg_database "
            "WHERE datname=current_database()"
        ).fetchone()
        expected = (self.owner_url.database, "t010_owner")
        if (
            row is None
            or row[:2] != expected
            or not 160000 <= row[2] < 170000
            or row[3:] != ("on", "on", self.marker)
        ):
            pytest.fail("disposable_postgresql_target_not_verified", pytrace=False)


def read_config(path: Path) -> Target:
    """An environment variable alone is never target authorization."""
    try:
        if (
            path.is_symlink()
            or stat.S_IMODE(path.stat().st_mode) != 0o600
            or path.stat().st_uid != os.geteuid()
            or stat.S_IMODE(path.parent.stat().st_mode) != 0o700
        ):
            raise ValueError
        data = json.loads(path.read_text())
        if (
            set(data)
            != {"version", "task", "run_id", "container_id", "postgres_image_id", "owner_url"}
            or data["version"] != 1
            or data["task"] != "T010"
            or not re.fullmatch(r"[0-9a-f]{12}", data["run_id"])
            or not re.fullmatch(r"[0-9a-f]{64}", data["container_id"])
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", data["postgres_image_id"])
        ):
            raise ValueError
        url = database_url(data["owner_url"])
        if (
            url.host != "slotbook-t010-" + data["run_id"]
            or url.database != "slotbook_t010_" + data["run_id"] + "_control"
            or url.username != "t010_owner"
            or not url.password
            or url.query
        ):
            raise ValueError
        return Target(data["run_id"], url)
    except (OSError, ValueError, TypeError, KeyError, DatabaseConfigurationError):
        pytest.fail("disposable_postgresql_config_invalid", pytrace=False)


@dataclass(repr=False)
class PostgreSQLCase:
    target: Target
    name: str
    private_directory: Path
    upgrades: int = 0

    def connection(self, role="owner"):
        return connect(self.target.url(self.name, role))

    def upgrade(self):
        self.upgrades += 1
        paths = [
            self.private_directory / f"migration-{self.upgrades}.{suffix}"
            for suffix in ("stdout", "stderr")
        ]
        with (
            os.fdopen(os.open(paths[0], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as out,
            os.fdopen(os.open(paths[1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as err,
        ):
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    str(BACKEND / "alembic.ini"),
                    "upgrade",
                    "head",
                ],
                cwd=BACKEND,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                timeout=30,
                env={
                    "PATH": os.defpath,
                    "TZ": "UTC",
                    "PYTHONTZPATH": "",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "MIGRATION_DATABASE_URL": self.target.url(self.name).render_as_string(
                        hide_password=False
                    ),
                },
            )
        if result.returncode:
            pytest.fail("postgresql_migration_fixture_failed", pytrace=False)


@pytest.fixture
def pg_database(private_runtime_dir) -> Iterator[PostgreSQLCase]:
    configured = os.environ.get("SLOTBOOK_TEST_DATABASE_CONFIG")
    if not configured:
        pytest.fail("disposable_postgresql_fixture_required", pytrace=False)
    path = Path(configured)
    target = read_config(path)
    with path.open("rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with connect(target.owner_url, autocommit=True) as control:
            target.verify_control(control)
            name = "slotbook_t010_" + target.run_id + "_" + uuid4().hex[:12]
            case = PostgreSQLCase(target, name, private_runtime_dir)
            control.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            try:
                control.execute(
                    sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                        sql.Identifier(name), sql.Literal(target.marker)
                    )
                )
                case.upgrade()
                for role in ("runtime", "backup"):
                    control.execute(
                        sql.SQL("GRANT {} TO {}").format(
                            sql.Identifier("slotbook_" + role), sql.Identifier("t010_" + role)
                        )
                    )
                yield case
            finally:
                target.verify_control(control)
                marker = control.execute(
                    "SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=%s",
                    (name,),
                ).fetchone()
                if marker != (target.marker,):
                    pytest.fail("disposable_case_cleanup_not_verified", pytrace=False)
                # Never FORCE or terminate another process to make cleanup pass.
                control.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def require_relations(connection, *relations):
    for relation in relations:
        if connection.execute("SELECT to_regclass(%s)", (relation,)).fetchone()[0] is None:
            pytest.fail("missing_mapped_relation:" + relation, pytrace=False)


@contextmanager
def rejected(connection, *sqlstates):
    """A real SQL violation must occur; missing tables/permissions cannot stand in."""
    with pytest.raises(psycopg.Error) as error, connection.transaction():
        yield
    assert error.value.sqlstate in sqlstates


@pytest.mark.parametrize("driver", ["sqlite://", "sqlite+pysqlite:///:memory:"])
def test_sqlite_substitution_is_rejected_before_connect(driver, monkeypatch):
    called = []
    monkeypatch.setattr(psycopg, "connect", lambda **kwargs: called.append(True))
    with pytest.raises(DatabaseConfigurationError, match="database_url_invalid"):
        connect(driver)
    assert not called


def test_foundation_uses_real_independent_postgresql_16_connections(pg_database):
    with pg_database.connection() as first, pg_database.connection() as second:
        assert first is not second
        assert first.execute("SELECT pg_backend_pid()").fetchone() != (
            second.execute("SELECT pg_backend_pid()").fetchone()
        )
        assert first.execute(
            "SELECT current_setting('fsync'),current_setting('synchronous_commit'),"
            "current_setting('TimeZone'),current_setting('transaction_isolation')"
        ).fetchone() == ("on", "on", "UTC", "read committed")
        assert first.execute(
            "SELECT extname FROM pg_extension WHERE extname='btree_gist'"
        ).fetchone() == ("btree_gist",)
        assert first.execute("SELECT nspname FROM pg_namespace WHERE nspname='private'").fetchone()


@pytest.mark.parametrize(
    "relation",
    [
        *("public." + name for name in PUBLIC_TABLES),
        *("private." + name for name in PRIVATE_TABLES),
    ],
)
def test_empty_upgrade_creates_mapped_table(pg_database, relation):
    with pg_database.connection() as connection:
        require_relations(connection, relation)


def test_repeat_upgrade_preserves_revision_and_catalog(pg_database):
    def snapshot():
        with pg_database.connection() as connection:
            return (
                set(
                    row[0] for row in connection.execute("SELECT version_num FROM alembic_version")
                ),
                connection.execute(
                    "SELECT schemaname,tablename FROM pg_tables "
                    "WHERE schemaname IN ('public','private') ORDER BY 1,2"
                ).fetchall(),
            )

    before = snapshot()
    heads = set(ScriptDirectory.from_config(Config(str(BACKEND / "alembic.ini"))).get_heads())
    assert before[0] == heads
    pg_database.upgrade()
    assert snapshot() == before


def test_booking_history_has_exactly_the_six_approved_columns(pg_database):
    with pg_database.connection() as connection:
        require_relations(connection, "public.bookings")
        columns = connection.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='bookings'"
        ).fetchall()
        assert {row[0] for row in columns} == HISTORY_COLUMNS


def test_instant_and_local_clock_columns_have_correct_postgresql_types(pg_database):
    with pg_database.connection() as connection:
        require_relations(connection, "public.bookings", "public.weekly_windows")
        for table, columns, expected in (
            ("bookings", ("starts_at", "ends_at", "canceled_at"), "timestamp with time zone"),
            ("weekly_windows", ("start_local_time", "end_local_time"), "time without time zone"),
        ):
            actual = dict(
                connection.execute(
                    "SELECT column_name,data_type FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=%s AND column_name=ANY(%s)",
                    (table, list(columns)),
                ).fetchall()
            )
            assert actual == dict.fromkeys(columns, expected)


@pytest.mark.parametrize(
    "violation", ["sqlite", "host", "database", "permissions", "extra", "task"]
)
def test_fixture_configuration_rejects_unapproved_targets(private_runtime_dir, violation):
    run_id = uuid4().hex[:12]
    url = URL.create(
        "postgresql+psycopg",
        username="t010_owner",
        password=uuid4().hex,
        host="slotbook-t010-" + run_id,
        database="slotbook_t010_" + run_id + "_control",
    )
    config = {
        "version": 1,
        "task": "T010",
        "run_id": run_id,
        "container_id": "a" * 64,
        "postgres_image_id": "sha256:" + "b" * 64,
        "owner_url": url.render_as_string(hide_password=False),
    }
    if violation == "sqlite":
        config["owner_url"] = "sqlite:///:memory:"
    elif violation == "host":
        config["owner_url"] = url.set(host="unapproved.invalid").render_as_string(
            hide_password=False
        )
    elif violation == "database":
        config["owner_url"] = url.set(database="unapproved").render_as_string(hide_password=False)
    elif violation == "extra":
        config["unapproved"] = True
    elif violation == "task":
        config["task"] = "unapproved"
    path = private_runtime_dir / "synthetic-target.json"
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as file:
        json.dump(config, file)
    if violation == "permissions":
        path.chmod(0o644)
    with pytest.raises(pytest.fail.Exception, match="disposable_postgresql_config_invalid"):
        read_config(path)
