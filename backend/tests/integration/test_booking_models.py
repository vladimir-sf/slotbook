"""T012 persistence/privacy tests, using unchanged T010 disposable fixtures."""

from datetime import UTC, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import inspect, select

from app.db.session import Database, create_database_engine
from app.models import Booking, BookingContact
from app.time import elapsed_after
from tests.integration.test_constraints import START, activity, booking
from tests.integration.test_migrations import pg_database as pg_database
from tests.integration.test_migrations import connect, rejected

pytestmark = [pytest.mark.integration, pytest.mark.privacy]
BACKEND = Path(__file__).resolve().parents[2]


def contact(connection, reference, **changes):
    values = dict(
        booking_id=reference,
        attendee_name="Synthetic attendee",
        attendee_email="synthetic@example.invalid",
        delete_at=START + timedelta(hours=721),
    )
    values.update(changes)
    connection.execute(
        "INSERT INTO private.booking_contacts (booking_id,attendee_name,attendee_email,delete_at) "
        "VALUES (%(booking_id)s,%(attendee_name)s,%(attendee_email)s,%(delete_at)s)",
        values,
    )


def history(connection, reference):
    return connection.execute(
        "SELECT id,activity_id,starts_at,ends_at,status,canceled_at "
        "FROM public.bookings WHERE id=%s",
        (reference,),
    ).fetchone()


def test_orm_round_trip_and_contact_deletion_preserve_the_complete_history(pg_database):
    with pg_database.connection() as owner:
        identifier = activity(owner)
    engine = create_database_engine(pg_database.target.url(pg_database.name, "runtime"))
    try:
        database = Database(engine)
        supplied = START.astimezone(timezone(timedelta(hours=5, minutes=30)))
        with database.transaction() as session:
            record = Booking(
                activity_id=identifier,
                starts_at=supplied,
                ends_at=supplied + timedelta(hours=1),
                status="confirmed",
            )
            session.add(record)
            session.flush()
            reference = record.id
            session.add(
                BookingContact(
                    booking_id=reference,
                    attendee_name=" Synthetic  Attendee ",
                    attendee_email="Synthetic.Local+Tag@example.invalid",
                    delete_at=elapsed_after(record.ends_at, timedelta(hours=720)),
                )
            )
        with pg_database.connection() as owner:
            before = history(owner, reference)
        with database.transaction() as session:
            record = session.get(Booking, reference)
            assert (
                record is not None and record.starts_at == START and record.starts_at.tzinfo is UTC
            )
            personal = session.get(BookingContact, reference)
            assert personal is not None and personal.attendee_name == " Synthetic  Attendee "
            assert personal.attendee_email == "Synthetic.Local+Tag@example.invalid"
            assert personal.delete_at == START + timedelta(hours=721)
            session.delete(personal)
        with database.transaction() as session:
            assert session.scalars(select(BookingContact)).all() == []
        with pg_database.connection() as owner:
            assert history(owner, reference) == before
    finally:
        engine.dispose()


@pytest.mark.parametrize("field", ["booking_id", "attendee_name", "attendee_email", "delete_at"])
def test_contact_rows_cannot_be_partial(pg_database, field):
    with pg_database.connection() as owner:
        reference = booking(owner, activity(owner))
        with rejected(owner, "23502"):
            contact(owner, reference, **{field: None})


def test_contact_is_optional_unique_and_must_reference_a_booking(pg_database):
    with pg_database.connection() as owner:
        reference = booking(owner, activity(owner))
        assert owner.execute("SELECT count(*) FROM private.booking_contacts").fetchone() == (0,)
        with rejected(owner, "23503"):
            contact(owner, uuid4())
        contact(owner, reference)
        with rejected(owner, "23505"):
            contact(owner, reference)
        with rejected(owner, "23503"):
            owner.execute("DELETE FROM public.bookings WHERE id=%s", (reference,))


@pytest.mark.parametrize("field", ["id", "activity_id", "starts_at", "ends_at"])
def test_direct_owner_sql_cannot_rewrite_retained_identity_or_interval(pg_database, field):
    with pg_database.connection() as owner:
        reference = booking(owner, activity(owner))
        replacements = {
            "id": uuid4(),
            "activity_id": activity(owner),
            "starts_at": START - timedelta(minutes=1),
            "ends_at": START + timedelta(hours=2),
        }
        before = history(owner, reference)
        with rejected(owner, "23514"):
            owner.execute(
                sql.SQL("UPDATE public.bookings SET {}=%s WHERE id=%s").format(
                    sql.Identifier(field)
                ),
                (replacements[field], reference),
            )
        assert history(owner, reference) == before


def test_cancellation_is_monotonic_preserves_first_timestamp_and_allows_noop(pg_database):
    with pg_database.connection() as owner:
        reference = booking(owner, activity(owner))
    first = START - timedelta(hours=1)
    with pg_database.connection("runtime") as runtime:
        update = "UPDATE public.bookings SET status='canceled',canceled_at=%s WHERE id=%s"
        runtime.execute(update, (first, reference))
        before = history(runtime, reference)
        runtime.execute(update, (first, reference))
        assert history(runtime, reference) == before
        with rejected(runtime, "23514"):
            runtime.execute(update, (first + timedelta(seconds=1), reference))
        with rejected(runtime, "23514"):
            runtime.execute(
                "UPDATE public.bookings SET status='confirmed',canceled_at=NULL WHERE id=%s",
                (reference,),
            )
        assert history(runtime, reference) == before


def test_runtime_cannot_edit_immutable_fields_delete_history_or_rewrite_contacts(pg_database):
    with pg_database.connection() as owner:
        reference = booking(owner, activity(owner))
        contact(owner, reference)
    with pg_database.connection("runtime") as runtime:
        for field in ("id", "activity_id", "starts_at", "ends_at"):
            with rejected(runtime, "42501"):
                runtime.execute(
                    sql.SQL("UPDATE public.bookings SET {}={} WHERE id=%s").format(
                        sql.Identifier(field), sql.Identifier(field)
                    ),
                    (reference,),
                )
        with rejected(runtime, "42501"):
            runtime.execute("DELETE FROM public.bookings WHERE id=%s", (reference,))
        for field in ("booking_id", "attendee_name", "attendee_email"):
            with rejected(runtime, "42501"):
                runtime.execute(
                    sql.SQL("UPDATE private.booking_contacts SET {}={} WHERE booking_id=%s").format(
                        sql.Identifier(field), sql.Identifier(field)
                    ),
                    (reference,),
                )
        # The indexed deadline can be updated by a later cancellation transaction.
        runtime.execute(
            "UPDATE private.booking_contacts SET delete_at=delete_at WHERE booking_id=%s",
            (reference,),
        )


def test_backup_cannot_read_a_future_history_column_or_private_contact(pg_database):
    with pg_database.connection() as owner:
        reference = booking(owner, activity(owner))
        contact(owner, reference)
        owner.execute("ALTER TABLE public.bookings ADD COLUMN synthetic_unapproved text")
        owner.execute("UPDATE public.bookings SET synthetic_unapproved='Synthetic marker'")
    with pg_database.connection("backup") as backup:
        assert history(backup, reference)
        for query in (
            "SELECT synthetic_unapproved FROM public.bookings",
            "SELECT * FROM private.booking_contacts",
            "SELECT public.bookings.*,private.booking_contacts.attendee_email "
            "FROM public.bookings JOIN private.booking_contacts ON id=booking_id",
        ):
            with rejected(backup, "42501"):
                backup.execute(query)


def test_migration_matches_both_models_and_indexes_contact_deadline(pg_database):
    engine = create_database_engine(pg_database.target.url(pg_database.name))
    try:
        inspector = inspect(engine)
        for table in (Booking.__table__, BookingContact.__table__):
            columns = inspector.get_columns(table.name, schema=table.schema)
            assert {column["name"] for column in columns} == set(table.columns.keys())
            for column in columns:
                declared = table.columns[column["name"]]
                assert column["nullable"] == declared.nullable
                assert str(column["type"].compile(dialect=engine.dialect)) == str(
                    declared.type.compile(dialect=engine.dialect)
                )
            assert inspector.get_pk_constraint(table.name, schema=table.schema)[
                "constrained_columns"
            ] == list(table.primary_key.columns.keys())
            foreign_keys = inspector.get_foreign_keys(
                table.name, schema=table.schema, postgresql_ignore_search_path=True
            )
            assert len(foreign_keys) == 1 and foreign_keys[0]["options"]["ondelete"] == "RESTRICT"
        assert any(
            index["column_names"] == ["delete_at"]
            for index in inspector.get_indexes("booking_contacts", schema="private")
        )
    finally:
        engine.dispose()


def test_history_trigger_is_not_a_privilege_escalation_function(pg_database):
    with pg_database.connection() as owner:
        assert owner.execute(
            "SELECT prosecdef,proconfig FROM pg_proc "
            "WHERE oid='private.preserve_booking_history()'::regprocedure"
        ).fetchone() == (False, ["search_path=pg_catalog"])
        for role in ("slotbook_runtime", "slotbook_backup"):
            assert not owner.execute(
                "SELECT has_function_privilege(%s,'private.preserve_booking_history()','EXECUTE')",
                (role,),
            ).fetchone()[0]


def test_booking_checks_are_stable_without_waiting_for_future_attempt_tables(pg_database):
    with pg_database.connection() as owner:
        checks = owner.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid='public.bookings'::regclass AND contype='c'"
        ).fetchall()
        assert len(checks) == 3
        forbidden = (
            "now(",
            "current_time",
            "clock_timestamp(",
            "statement_timestamp(",
            "transaction_timestamp(",
            "current_date",
            "localtime",
            "timeofday(",
            "select ",
        )
        assert all(
            not any(token in definition.lower() for token in forbidden) for (definition,) in checks
        )


def test_upgrade_from_populated_configuration_and_repeat_preserve_data(pg_database, monkeypatch):
    target = pg_database.target
    name = "slotbook_t010_" + target.run_id + "_" + uuid4().hex[:12]
    with connect(target.owner_url, autocommit=True) as control:
        target.verify_control(control)
        control.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            control.execute(
                sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                    sql.Identifier(name), sql.Literal(target.marker)
                )
            )
            with monkeypatch.context() as configuration:
                configuration.setenv(
                    "MIGRATION_DATABASE_URL", target.url(name).render_as_string(hide_password=False)
                )
                config = Config(str(BACKEND / "alembic.ini"))
                command.upgrade(config, "0002_configuration")
                with connect(target.url(name)) as owner:
                    identifier = activity(owner)
                command.upgrade(config, "head")
                with connect(target.url(name)) as owner:
                    reference = booking(owner, identifier)
                    contact(owner, reference)
                    before = history(owner, reference)
                command.upgrade(config, "head")
                with connect(target.url(name)) as owner:
                    assert history(owner, reference) == before
                    assert owner.execute("SELECT count(*) FROM public.activities").fetchone() == (
                        1,
                    )
                    assert owner.execute(
                        "SELECT count(*) FROM private.booking_contacts"
                    ).fetchone() == (1,)
        finally:
            target.verify_control(control)
            marker = control.execute(
                "SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=%s",
                (name,),
            ).fetchone()
            assert marker == (target.marker,)
            control.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
