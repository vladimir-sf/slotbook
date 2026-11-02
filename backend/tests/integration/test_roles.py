"""T010 privilege checks use real unprivileged logins, never owner SET ROLE."""

from datetime import timedelta

import pytest
from psycopg import sql

from tests.integration.test_constraints import START, activity, booking
from tests.integration.test_migrations import pg_database as pg_database
from tests.integration.test_migrations import (
    HISTORY_COLUMNS,
    PRIVATE_TABLES,
    rejected,
    require_relations,
)

pytestmark = [pytest.mark.integration, pytest.mark.privacy]


def test_runtime_backup_groups_have_no_elevation_or_ddl_permissions(pg_database):
    with pg_database.connection() as owner:
        attributes = owner.execute(
            "SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolinherit,"
            "rolreplication,rolbypassrls FROM pg_roles "
            "WHERE rolname IN ('slotbook_runtime','slotbook_backup') ORDER BY rolname"
        ).fetchall()
        assert attributes == [
            (name, False, False, False, False, False, False, False)
            for name in ("slotbook_backup", "slotbook_runtime")
        ]
        assert owner.execute(
            "SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member "
            "WHERE r.rolname IN ('slotbook_runtime','slotbook_backup')"
        ).fetchone() == (0,)
        for role in ("slotbook_runtime", "slotbook_backup"):
            for privilege in ("CREATE", "TEMP"):
                assert not owner.execute(
                    "SELECT has_database_privilege(%s,current_database(),%s)", (role, privilege)
                ).fetchone()[0]
            for schema in ("public", "private"):
                assert not owner.execute(
                    "SELECT has_schema_privilege(%s,%s,'CREATE')", (role, schema)
                ).fetchone()[0]
        assert not owner.execute(
            "SELECT has_schema_privilege('slotbook_backup','private','USAGE')"
        ).fetchone()[0]
        assert not owner.execute(
            "SELECT has_database_privilege('t010_outsider',current_database(),'CONNECT')"
        ).fetchone()[0]
    for role in ("runtime", "backup"):
        with pg_database.connection(role) as connection:
            assert connection.execute("SELECT current_user,session_user").fetchone() == (
                "t010_" + role,
                "t010_" + role,
            )
            for statement in (
                "CREATE TABLE public.t010_forbidden (id int)",
                "CREATE TEMP TABLE t010_forbidden (id int)",
                "SELECT * FROM public.alembic_version",
            ):
                with rejected(connection, "42501"):
                    connection.execute(statement)


def test_future_tables_receive_no_default_backup_access(pg_database):
    with pg_database.connection() as owner:
        owner.execute("CREATE TABLE public.t010_future_probe (id int)")
        owner.execute("CREATE TABLE private.t010_future_probe (id int)")
        owner.execute("INSERT INTO public.t010_future_probe VALUES (1)")
        owner.execute("INSERT INTO private.t010_future_probe VALUES (1)")
    with pg_database.connection("backup") as backup:
        for schema in ("public", "private"):
            with rejected(backup, "42501"):
                backup.execute(
                    sql.SQL("SELECT * FROM {}.t010_future_probe").format(sql.Identifier(schema))
                )


@pytest.mark.parametrize("table", ["activities", "weekly_windows", "blocked_dates"])
def test_backup_can_read_explicit_configuration_allowlist(pg_database, table):
    with pg_database.connection() as owner:
        require_relations(owner, "public." + table)
    with pg_database.connection("backup") as backup:
        backup.execute(sql.SQL("SELECT * FROM public.{}").format(sql.Identifier(table)))
        assert backup.execute(
            "SELECT has_table_privilege(current_user,%s,'INSERT')", ("public." + table,)
        ).fetchone() == (False,)
        assert backup.execute(
            "SELECT has_table_privilege(current_user,%s,'UPDATE')", ("public." + table,)
        ).fetchone() == (False,)
        assert backup.execute(
            "SELECT has_table_privilege(current_user,%s,'DELETE')", ("public." + table,)
        ).fetchone() == (False,)


@pytest.mark.parametrize("table", PRIVATE_TABLES)
def test_backup_cannot_read_any_private_table(pg_database, table):
    with pg_database.connection() as owner:
        # A missing relation or UndefinedTable error must never prove isolation.
        require_relations(owner, "private." + table)
    with pg_database.connection("backup") as backup:
        with rejected(backup, "42501"):
            backup.execute(sql.SQL("SELECT * FROM private.{}").format(sql.Identifier(table)))


def test_runtime_can_manage_contacts_without_granting_backup_access(pg_database):
    with pg_database.connection() as owner:
        require_relations(owner, "public.activities", "public.bookings", "private.booking_contacts")
    with pg_database.connection("runtime") as runtime:
        identifier = activity(runtime)
        reference = booking(runtime, identifier)
        runtime.execute(
            "INSERT INTO private.booking_contacts "
            "(booking_id,attendee_name,attendee_email,delete_at) VALUES (%s,%s,%s,%s)",
            (
                reference,
                "Synthetic attendee",
                "synthetic@example.invalid",
                START + timedelta(hours=721),
            ),
        )
        assert runtime.execute("SELECT booking_id FROM private.booking_contacts").fetchone() == (
            reference,
        )
    with pg_database.connection("backup") as backup:
        columns = sorted(HISTORY_COLUMNS)
        row = backup.execute(
            sql.SQL("SELECT {} FROM public.bookings").format(
                sql.SQL(",").join(map(sql.Identifier, columns))
            )
        ).fetchone()
        assert row is not None
        assert row[columns.index("id")] == reference
        with rejected(backup, "42501"):
            backup.execute("SELECT attendee_name,attendee_email FROM private.booking_contacts")
        with rejected(backup, "42501"):
            backup.execute(
                "UPDATE public.bookings SET status='canceled',canceled_at=%s WHERE id=%s",
                (START, reference),
            )
    with pg_database.connection("runtime") as runtime:
        runtime.execute("DELETE FROM private.booking_contacts WHERE booking_id=%s", (reference,))
        assert runtime.execute(
            "SELECT id FROM public.bookings WHERE id=%s", (reference,)
        ).fetchone() == (reference,)


def test_backup_booking_privileges_are_only_the_six_retained_columns(pg_database):
    with pg_database.connection() as owner:
        require_relations(owner, "public.bookings")
        granted = owner.execute(
            "SELECT column_name,privilege_type,is_grantable FROM information_schema."
            "column_privileges WHERE grantee='slotbook_backup' "
            "AND table_schema='public' AND table_name='bookings'"
        ).fetchall()
        assert set(granted) == {(column, "SELECT", "NO") for column in HISTORY_COLUMNS}
        # Table-level SELECT would automatically expose future columns.
        assert not owner.execute(
            "SELECT has_table_privilege('slotbook_backup','public.bookings','SELECT')"
        ).fetchone()[0]
