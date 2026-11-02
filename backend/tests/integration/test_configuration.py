"""T011 configuration acceptance; T010 assertions remain unchanged and visible."""

from datetime import date, time

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.db.session import Database, create_database_engine
from app.models import Activity, BlockedDate, WeeklyWindow
from tests.integration.test_constraints import activity, window
from tests.integration.test_migrations import pg_database as pg_database
from tests.integration.test_migrations import rejected

pytestmark = pytest.mark.integration


@pytest.fixture
def runtime_engine(pg_database):
    engine = create_database_engine(pg_database.target.url(pg_database.name, "runtime"))
    try:
        yield engine
    finally:
        engine.dispose()


def test_orm_round_trip_uses_real_types_defaults_and_configuration_permissions(runtime_engine):
    database = Database(runtime_engine)
    boundary = time(9, 0, 0, 123456)
    with database.transaction() as session:
        record = Activity(
            slug="synthetic-orm",
            title="Synthetic title",
            description="\u2003📘 Text\n  <literal>\u3000",
            duration_minutes=60,
            timezone="Europe/Vienna",
            is_active=True,
        )
        session.add(record)
        session.flush()
        assert record.id is not None
        identifier = record.id
        schedule = WeeklyWindow(
            activity_id=identifier,
            iso_weekday=1,
            start_local_time=boundary,
            end_local_time=time(10),
        )
        session.add_all(
            [schedule, BlockedDate(activity_id=identifier, local_date=date(2030, 1, 2))]
        )
        session.flush()
        schedule_id = schedule.id
    with database.transaction() as session:
        restored = session.get(Activity, identifier)
        assert restored is not None and restored.description == "📘 Text\n  <literal>"
        assert restored.timezone == "Europe/Vienna"
        restored.description = "\tUpdated 📘\n  literal\t"
        saved_window = session.get(WeeklyWindow, schedule_id)
        assert saved_window is not None and saved_window.start_local_time == boundary
        saved_window.end_local_time = time(10, 30)
        assert session.get(BlockedDate, (identifier, date(2030, 1, 2))) is not None
    with database.transaction() as session:
        updated = session.get(Activity, identifier)
        assert updated is not None and updated.description == "Updated 📘\n  literal"
        saved_window = session.get(WeeklyWindow, schedule_id)
        assert saved_window is not None and saved_window.end_local_time == time(10, 30)
        session.delete(saved_window)
    with database.transaction() as session:
        assert session.scalars(select(WeeklyWindow)).all() == []


def test_invalid_replacement_rolls_back_deletion_and_all_new_windows(pg_database, runtime_engine):
    with pg_database.connection() as owner:
        identifier = activity(owner)
        window(owner, identifier)
        original = owner.execute(
            "SELECT id,start_local_time,end_local_time FROM public.weekly_windows"
        ).fetchall()
    database = Database(runtime_engine)
    with pytest.raises(IntegrityError) as error, database.transaction() as session:
        session.execute(
            text("DELETE FROM public.weekly_windows WHERE activity_id=:id"), {"id": identifier}
        )
        session.add_all(
            [
                WeeklyWindow(
                    activity_id=identifier,
                    iso_weekday=1,
                    start_local_time=time(9),
                    end_local_time=time(10),
                ),
                WeeklyWindow(
                    activity_id=identifier,
                    iso_weekday=1,
                    start_local_time=time(9, 30),
                    end_local_time=time(10, 30),
                ),
            ]
        )
        session.flush()
    assert error.value.orig.sqlstate == "23P01"
    with pg_database.connection() as check:
        assert (
            check.execute(
                "SELECT id,start_local_time,end_local_time FROM public.weekly_windows"
            ).fetchall()
            == original
        )


@pytest.mark.parametrize(
    "description",
    ["", "\u2003", "📘" * 2001, " padded "],
    ids=["empty", "blank", "overlong", "unnormalized"],
)
def test_description_database_check_blocks_invalid_direct_writes(pg_database, description):
    with pg_database.connection() as connection:
        with rejected(connection, "23514"):
            activity(connection, description=description)


def test_description_database_check_uses_the_same_unicode_trim_set(pg_database):
    with pg_database.connection() as connection:
        maximum = "📘" * 2000
        identifier = activity(connection, description=maximum)
        assert connection.execute(
            "SELECT char_length(description) FROM public.activities WHERE id=%s", (identifier,)
        ).fetchone() == (2000,)
        for code in range(0x110000):
            padding = chr(code)
            if padding.isspace():
                with rejected(connection, "23514"):
                    activity(connection, description=padding + "Synthetic" + padding)


def test_end_of_day_24_hour_label_is_not_a_frozen_local_clock(pg_database):
    with pg_database.connection() as connection:
        identifier = activity(connection)
        with rejected(connection, "23514"):
            connection.execute(
                "INSERT INTO public.weekly_windows "
                "(activity_id,iso_weekday,start_local_time,end_local_time) "
                "VALUES (%s,1,TIME '23:00',TIME '24:00')",
                (identifier,),
            )


def test_runtime_privileges_do_not_add_activity_delete_or_unblock_operations(pg_database):
    with pg_database.connection() as owner:
        identifier = activity(owner)
        owner.execute(
            "INSERT INTO public.blocked_dates (activity_id,local_date) VALUES (%s,%s)",
            (identifier, date(2030, 1, 2)),
        )
    with pg_database.connection("runtime") as runtime:
        for statement in (
            "DELETE FROM public.activities",
            "DELETE FROM public.blocked_dates",
            "UPDATE public.blocked_dates SET local_date=DATE '2030-01-03'",
        ):
            with rejected(runtime, "42501"):
                runtime.execute(statement)


def test_backup_configuration_grants_do_not_include_future_columns_or_writes(pg_database):
    with pg_database.connection() as owner:
        for table in ("activities", "weekly_windows", "blocked_dates"):
            columns = owner.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=%s",
                (table,),
            ).fetchall()
            grants = owner.execute(
                "SELECT column_name,privilege_type,is_grantable FROM information_schema."
                "column_privileges WHERE grantee='slotbook_backup' "
                "AND table_schema='public' AND table_name=%s",
                (table,),
            ).fetchall()
            assert set(grants) == {(column, "SELECT", "NO") for (column,) in columns}
            assert not owner.execute(
                "SELECT has_table_privilege('slotbook_backup',%s,'SELECT')", ("public." + table,)
            ).fetchone()[0]
        activity(owner)
        owner.execute("ALTER TABLE public.activities ADD COLUMN synthetic_unapproved text")
        owner.execute("UPDATE public.activities SET synthetic_unapproved='Synthetic marker'")
    with pg_database.connection("backup") as backup:
        assert backup.execute("SELECT slug FROM public.activities").fetchone()
        for statement in (
            "SELECT synthetic_unapproved FROM public.activities",
            "UPDATE public.activities SET title='Synthetic edit'",
            "DELETE FROM public.activities",
        ):
            with rejected(backup, "42501"):
                backup.execute(statement)


def test_migrated_column_types_nullability_and_keys_match_the_model_registry(pg_database):
    engine = create_database_engine(pg_database.target.url(pg_database.name))
    try:
        inspector = inspect(engine)
        assert {
            "alembic_version",
            "activities",
            "weekly_windows",
            "blocked_dates",
        } <= set(inspector.get_table_names(schema="public"))
        # This T011 regression must remain valid when later tables are mapped.
        for table in (Activity.__table__, WeeklyWindow.__table__, BlockedDate.__table__):
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
            for foreign_key in inspector.get_foreign_keys(
                table.name, schema=table.schema, postgresql_ignore_search_path=True
            ):
                assert foreign_key["referred_schema"] == "public"
                assert foreign_key["referred_table"] == "activities"
                assert foreign_key["options"]["ondelete"] == "RESTRICT"
    finally:
        engine.dispose()
