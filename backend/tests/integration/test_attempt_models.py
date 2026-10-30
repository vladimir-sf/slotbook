"""T013 real admission invariants; not RP-01–17/API/crash-recovery completion."""

from contextlib import contextmanager
from datetime import timedelta
from uuid import uuid4

import psycopg
import pytest
from psycopg.types.json import Jsonb

from tests.integration.test_constraints import START, activity, booking
from tests.integration.test_migrations import pg_database as pg_database
from tests.integration.test_migrations import rejected

pytestmark = pytest.mark.integration
DIGEST = bytes(range(32))
FINGERPRINT = "v1:" + "a" * 64


@contextmanager
def commit_rejected(database):
    # psycopg 3.3.6 __exit__ doesn't close when commit itself raises.
    connection = database.connection("runtime")
    try:
        with pytest.raises(psycopg.Error) as error, connection:
            yield connection
        assert error.value.sqlstate == "23514"
    finally:
        connection.close()


def admission(connection, generation, *, binding=True):
    row = connection.execute(
        "WITH stamp AS MATERIALIZED (SELECT clock_timestamp() AS t) "
        "INSERT INTO private.booking_attempts "
        "(generation,key_digest,first_received_at,expires_at,state) "
        "SELECT %s,%s,t,t+INTERVAL '24 hours','admitted' FROM stamp "
        "RETURNING first_received_at,expires_at",
        (generation, DIGEST),
    ).fetchone()
    if binding:
        connection.execute(
            "INSERT INTO private.attempt_bindings VALUES (%s,%s,%s)",
            (generation, DIGEST, FINGERPRINT),
        )
    return row


def test_admission_and_binding_commit_together_and_use_database_sample(pg_database):
    generation = uuid4()
    with pg_database.connection("runtime") as writer:
        receipt = admission(writer, generation)
        with pg_database.connection() as reader:
            assert reader.execute("SELECT count(*) FROM private.booking_attempts").fetchone() == (
                0,
            )
            assert reader.execute("SELECT count(*) FROM private.attempt_bindings").fetchone() == (
                0,
            )
        assert receipt[1] - receipt[0] == timedelta(hours=24)
    with pg_database.connection() as reader:
        assert (
            reader.execute(
                "SELECT first_received_at,expires_at FROM private.booking_attempts"
            ).fetchone()
            == receipt
        )
        assert reader.execute(
            "SELECT payload_fingerprint FROM private.attempt_bindings"
        ).fetchone() == (FINGERPRINT,)


def test_admission_without_binding_cannot_commit(pg_database):
    with commit_rejected(pg_database) as writer:
        admission(writer, uuid4(), binding=False)
    with pg_database.connection() as reader:
        assert reader.execute("SELECT count(*) FROM private.booking_attempts").fetchone() == (0,)


def test_unique_generation_digest_serializes_but_other_generations_are_independent(pg_database):
    generation = uuid4()
    with pg_database.connection() as owner:
        admission(owner, generation)
        with rejected(owner, "23505"):
            admission(owner, generation)
        admission(owner, uuid4())
        assert owner.execute("SELECT count(*) FROM private.booking_attempts").fetchone() == (2,)


@pytest.mark.parametrize("elapsed", [timedelta(hours=23), timedelta(hours=24, microseconds=1)])
def test_receipt_check_requires_exact_elapsed_day(pg_database, elapsed):
    with pg_database.connection() as owner:
        with rejected(owner, "23514"):
            owner.execute(
                "INSERT INTO private.booking_attempts "
                "(generation,key_digest,first_received_at,expires_at,state) "
                "VALUES (%s,%s,%s,%s,'expired')",
                (uuid4(), DIGEST, START, START + elapsed),
            )


def test_receipt_is_elapsed_not_dst_calendar_day(pg_database):
    with pg_database.connection() as owner:
        owner.execute("SET LOCAL TIME ZONE 'Europe/Vienna'")
        with rejected(owner, "23514"):
            owner.execute(
                "INSERT INTO private.booking_attempts "
                "(generation,key_digest,first_received_at,expires_at,state) VALUES "
                "(%s,%s,TIMESTAMPTZ '2030-03-30 12:00 Europe/Vienna',"
                "TIMESTAMPTZ '2030-03-31 12:00 Europe/Vienna','expired')",
                (uuid4(), DIGEST),
            )


def test_binding_claim_precedes_final_database_receipt_insert(pg_database):
    generation = uuid4()
    with pg_database.connection("runtime") as writer:
        writer.execute(
            "INSERT INTO private.attempt_bindings VALUES (%s,%s,%s)",
            (generation, DIGEST, FINGERPRINT),
        )
        final = admission(writer, generation, binding=False)
    with pg_database.connection() as reader:
        assert (
            reader.execute(
                "SELECT first_received_at,expires_at FROM private.booking_attempts"
            ).fetchone()
            == final
        )


def test_receipt_cannot_be_changed_even_in_the_inserting_transaction(pg_database):
    with commit_rejected(pg_database) as writer:
        admission(writer, uuid4())
        writer.execute(
            "UPDATE private.booking_attempts SET first_received_at=first_received_at+"
            "INTERVAL '1 second',expires_at=expires_at+INTERVAL '1 second'"
        )


def test_immediate_constraint_mode_cannot_bypass_receipt_immutability(pg_database):
    with pg_database.connection() as owner:
        admission(owner, uuid4())
    with commit_rejected(pg_database) as writer:
        writer.execute("SET CONSTRAINTS ALL IMMEDIATE")
        writer.execute("UPDATE private.booking_attempts SET state=state")
        writer.execute(
            "UPDATE private.booking_attempts SET first_received_at=first_received_at+"
            "INTERVAL '1 second',expires_at=expires_at+INTERVAL '1 second'"
        )


@pytest.mark.parametrize("prior_noop", [False, True])
def test_committed_receipt_cannot_be_restamped_even_after_another_update(pg_database, prior_noop):
    with pg_database.connection() as owner:
        admission(owner, uuid4())
    with commit_rejected(pg_database) as writer:
        if prior_noop:
            writer.execute("UPDATE private.booking_attempts SET state=state")
        writer.execute(
            "UPDATE private.booking_attempts SET first_received_at=first_received_at+"
            "INTERVAL '1 second',expires_at=expires_at+INTERVAL '1 second'"
        )


def test_expiry_removes_binding_result_links_and_keeps_tombstone_and_booking(pg_database):
    generation = uuid4()
    with pg_database.connection() as owner:
        reference = booking(owner, activity(owner))
        receipt = admission(owner, generation)
    with pg_database.connection("runtime") as writer:
        writer.execute(
            "UPDATE private.booking_attempts SET state='succeeded',booking_id=%s", (reference,)
        )
    with pg_database.connection("runtime") as writer:
        writer.execute("UPDATE private.booking_attempts SET state='expired'")
    with pg_database.connection("runtime") as reader:
        assert reader.execute(
            "SELECT generation,key_digest,first_received_at,expires_at,state,"
            "booking_id,rejection_status,rejection_code,rejection_fields "
            "FROM private.booking_attempts"
        ).fetchone() == (generation, DIGEST, *receipt, "expired", None, None, None, None)
        assert reader.execute("SELECT count(*) FROM private.attempt_bindings").fetchone() == (0,)
        assert reader.execute("SELECT id FROM public.bookings").fetchone() == (reference,)
        with rejected(reader, "42501"):
            reader.execute("DELETE FROM private.booking_attempts")
        with rejected(reader, "23514"):
            reader.execute("UPDATE private.booking_attempts SET state='admitted'")
    with commit_rejected(pg_database) as writer:
        writer.execute(
            "INSERT INTO private.attempt_bindings VALUES (%s,%s,%s)",
            (generation, DIGEST, FINGERPRINT),
        )


def test_operator_attempt_cleanup_cannot_cascade_delete_booking(pg_database):
    with pg_database.connection() as owner:
        reference = booking(owner, activity(owner))
        admission(owner, uuid4())
        owner.execute(
            "UPDATE private.booking_attempts SET state='succeeded',booking_id=%s", (reference,)
        )
    with pg_database.connection() as owner:
        owner.execute("DELETE FROM private.booking_attempts")
        assert owner.execute("SELECT id FROM public.bookings").fetchone() == (reference,)


@pytest.mark.parametrize(
    "fields",
    [
        [{"path": "attendeeEmail", "code": "invalid", "input": "Synthetic"}],
        [{"path": "body", "code": "Synthetic arbitrary data"}],
        {"message": "Synthetic arbitrary data"},
    ],
)
def test_rejection_metadata_cannot_store_free_text_or_inputs(pg_database, fields):
    with pg_database.connection() as owner:
        admission(owner, uuid4())
        with rejected(owner, "23514"):
            owner.execute(
                "UPDATE private.booking_attempts SET state='rejected',rejection_status=400,"
                "rejection_code='validation_failed',rejection_fields=%s",
                (Jsonb(fields),),
            )


def test_rejection_can_store_only_safe_codes_and_expiry_clears_them(pg_database):
    with pg_database.connection() as owner:
        admission(owner, uuid4())
    with pg_database.connection("runtime") as writer:
        writer.execute(
            "UPDATE private.booking_attempts SET state='rejected',rejection_status=400,"
            "rejection_code='validation_failed',rejection_fields=%s",
            (Jsonb([{"path": "body", "code": "invalid"}]),),
        )
    with pg_database.connection("runtime") as writer:
        writer.execute("UPDATE private.booking_attempts SET state='expired'")
        assert writer.execute(
            "SELECT rejection_fields FROM private.booking_attempts"
        ).fetchone() == (None,)


def test_generation_is_singleton_and_recovery_metadata_is_operator_only(pg_database):
    with pg_database.connection("runtime") as writer:
        writer.execute("INSERT INTO private.retry_generation VALUES (1,%s,%s)", (uuid4(), START))
        with rejected(writer, "23505"):
            writer.execute(
                "INSERT INTO private.retry_generation VALUES (1,%s,%s)", (uuid4(), START)
            )
        with rejected(writer, "42501"):
            writer.execute("UPDATE private.retry_generation SET generation=%s", (uuid4(),))
        with rejected(writer, "42501"):
            writer.execute(
                "INSERT INTO private.recovery_events "
                "(restored_at,snapshot_reference,new_generation,state_loss_reason) VALUES "
                "(%s,%s,%s,'qualified_unrecoverable_restore')",
                (START, uuid4(), uuid4()),
            )
