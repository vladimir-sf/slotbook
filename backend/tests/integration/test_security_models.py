"""T014 real PostgreSQL security/state acceptance without authentication services."""

from datetime import timedelta
from uuid import uuid4

import pytest
from argon2 import extract_parameters
from pwdlib import PasswordHash
from sqlalchemy import inspect

from app.db.session import create_database_engine
from tests.integration.test_constraints import START
from tests.integration.test_migrations import pg_database as pg_database
from tests.integration.test_migrations import rejected

pytestmark = [pytest.mark.integration, pytest.mark.privacy]
DIGEST = bytes(range(32))


@pytest.fixture(scope="module")
def encoded_hash():
    return PasswordHash.recommended().hash(uuid4().hex)


def admin(connection, encoded):
    return connection.execute(
        "INSERT INTO private.admins (email,password_hash) VALUES (%s,%s) RETURNING id",
        ("synthetic-admin@example.invalid", encoded),
    ).fetchone()[0]


def session(connection, identifier, *, elapsed=timedelta(hours=1), digest=DIGEST):
    connection.execute(
        "INSERT INTO private.admin_sessions (token_digest,admin_id,issued_at,expires_at) "
        "VALUES (%s,%s,%s,%s)",
        (digest, identifier, START, START + elapsed),
    )


@pytest.mark.parametrize("same_email", [True, False])
def test_database_has_exactly_one_admin_not_just_unique_email(
    pg_database, encoded_hash, same_email
):
    with pg_database.connection("runtime") as writer:
        admin(writer, encoded_hash)
        with rejected(writer, "23505"):
            writer.execute(
                "INSERT INTO private.admins (email,password_hash) VALUES (%s,%s)",
                (
                    "synthetic-admin@example.invalid" if same_email else "other@example.invalid",
                    encoded_hash,
                ),
            )


@pytest.mark.parametrize("kind", ["plaintext", "fast", "weak", "excessive"])
def test_database_rejects_raw_or_unsafe_password_storage(pg_database, encoded_hash, kind):
    parameters = extract_parameters(encoded_hash)
    value = {
        "plaintext": "synthetic-not-a-hash",
        "fast": "a" * 64,
        "weak": encoded_hash.replace("m=" + str(parameters.memory_cost), "m=8"),
        "excessive": encoded_hash.replace("t=" + str(parameters.time_cost), "t=99999999"),
    }[kind]
    with pg_database.connection("runtime") as writer:
        with rejected(writer, "23514"):
            admin(writer, value)


def test_argon2_round_trip_stores_only_a_verifiable_hash(pg_database):
    secret = uuid4().hex
    hasher = PasswordHash.recommended()
    encoded = hasher.hash(secret)
    with pg_database.connection("runtime") as writer:
        identifier = admin(writer, encoded)
    with pg_database.connection("runtime") as reader:
        stored = reader.execute(
            "SELECT password_hash FROM private.admins WHERE id=%s", (identifier,)
        ).fetchone()[0]
        assert stored != secret and hasher.verify(secret, stored)


@pytest.mark.parametrize("elapsed", [timedelta(minutes=59), timedelta(hours=1, microseconds=1)])
def test_session_expiry_is_exactly_sixty_elapsed_minutes(pg_database, encoded_hash, elapsed):
    with pg_database.connection("runtime") as writer:
        identifier = admin(writer, encoded_hash)
        with rejected(writer, "23514"):
            session(writer, identifier, elapsed=elapsed)


def test_session_hour_is_elapsed_even_across_dst_fold(pg_database, encoded_hash):
    with pg_database.connection("runtime") as writer:
        identifier = admin(writer, encoded_hash)
        writer.execute("SET LOCAL TIME ZONE 'Europe/Vienna'")
        writer.execute(
            "INSERT INTO private.admin_sessions VALUES (%s,%s,"
            "TIMESTAMPTZ '2030-10-27 02:30+02',TIMESTAMPTZ '2030-10-27 02:30+01')",
            (DIGEST, identifier),
        )
        assert writer.execute(
            "SELECT expires_at-issued_at FROM private.admin_sessions"
        ).fetchone() == (timedelta(hours=1),)


def test_digest_cardinality_foreign_key_and_session_lookup(pg_database, encoded_hash):
    with pg_database.connection("runtime") as writer:
        identifier = admin(writer, encoded_hash)
        with rejected(writer, "23514"):
            session(writer, identifier, digest=b"short")
        with rejected(writer, "23503"):
            session(writer, uuid4())
        session(writer, identifier)
        with rejected(writer, "23505"):
            session(writer, identifier)
        assert writer.execute(
            "SELECT admin_id FROM private.admin_sessions WHERE token_digest=%s", (DIGEST,)
        ).fetchone() == (identifier,)


def test_sessions_cannot_refresh_even_for_owner_and_runtime_can_revoke(pg_database, encoded_hash):
    with pg_database.connection("runtime") as writer:
        identifier = admin(writer, encoded_hash)
        session(writer, identifier)
        with rejected(writer, "42501"):
            writer.execute("UPDATE private.admin_sessions SET issued_at=issued_at")
        with rejected(writer, "42501"):
            writer.execute("UPDATE private.admins SET password_hash=password_hash")
    with pg_database.connection() as owner:
        with rejected(owner, "23514"):
            owner.execute(
                "UPDATE private.admin_sessions SET issued_at=issued_at+INTERVAL '1 minute',"
                "expires_at=expires_at+INTERVAL '1 minute'"
            )
    with pg_database.connection("runtime") as writer:
        writer.execute("DELETE FROM private.admin_sessions WHERE token_digest=%s", (DIGEST,))
        assert writer.execute("SELECT id FROM private.admins").fetchone() == (identifier,)


@pytest.mark.parametrize(
    "values", [(2, 0, None), (1, -1, None), (1, 0, "Synthetic private exception detail")]
)
def test_worker_status_rejects_non_singleton_negative_counts_and_raw_errors(pg_database, values):
    with pg_database.connection("runtime") as writer:
        with rejected(writer, "23514"):
            writer.execute(
                "INSERT INTO private.worker_status (id,overdue_count,safe_failure_code) "
                "VALUES (%s,%s,%s)",
                values,
            )


def test_worker_status_is_explicit_safe_and_repeat_upgrade_preserves_all_state(
    pg_database, encoded_hash
):
    with pg_database.connection("runtime") as writer:
        assert writer.execute("SELECT count(*) FROM private.worker_status").fetchone() == (0,)
        identifier = admin(writer, encoded_hash)
        session(writer, identifier)
        writer.execute(
            "INSERT INTO private.worker_status (id,overdue_count,safe_failure_code) "
            "VALUES (1,2,'worker_not_started')"
        )
        writer.execute(
            "UPDATE private.worker_status SET last_heartbeat=%s,last_successful_purge=%s,"
            "safe_failure_code=NULL WHERE id=1",
            (START, START),
        )
        before = writer.execute("SELECT * FROM private.worker_status").fetchall()
    pg_database.upgrade()
    with pg_database.connection("runtime") as reader:
        assert reader.execute("SELECT * FROM private.worker_status").fetchall() == before
        assert reader.execute("SELECT password_hash FROM private.admins").fetchone() == (
            encoded_hash,
        )
        assert reader.execute("SELECT count(*) FROM private.admin_sessions").fetchone() == (1,)


def test_deadline_and_lookup_indexes_are_valid_and_no_history_fields_are_added(pg_database):
    engine = create_database_engine(pg_database.target.url(pg_database.name))
    try:
        inspector = inspect(engine)
        assert any(
            i["column_names"] == ["expires_at"]
            for i in inspector.get_indexes("admin_sessions", schema="private")
        )
        assert inspector.get_pk_constraint("admin_sessions", schema="private")[
            "constrained_columns"
        ] == ["token_digest"]
    finally:
        engine.dispose()
    with pg_database.connection() as owner:
        assert owner.execute(
            "SELECT count(*) FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid "
            "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='private' "
            "AND c.relname='one_admin' AND i.indisunique AND i.indisvalid"
        ).fetchone() == (1,)
        assert owner.execute(
            "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' "
            "AND table_name='bookings'"
        ).fetchone() == (6,)
