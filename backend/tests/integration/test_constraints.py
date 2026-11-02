"""T010 database-enforced invariants; no ORM or application validation shortcut."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time, timedelta
from queue import Queue
from time import monotonic, sleep
from uuid import uuid4

import psycopg
import pytest

from tests.integration.test_migrations import pg_database as pg_database
from tests.integration.test_migrations import rejected, require_relations

pytestmark = pytest.mark.integration
START = datetime(2030, 1, 1, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    "relation,kind",
    [
        ("public.activities", "c"),
        ("public.weekly_windows", "c"),
        ("public.weekly_windows", "x"),
        ("public.bookings", "c"),
        ("public.bookings", "x"),
        ("public.weekly_windows", "f"),
        ("public.blocked_dates", "f"),
        ("public.bookings", "f"),
        ("private.booking_attempts", "c"),
    ],
)
def test_required_database_constraints_exist(pg_database, relation, kind):
    with pg_database.connection() as connection:
        constraints = connection.execute(
            "SELECT conname FROM pg_constraint WHERE conrelid=to_regclass(%s) AND contype=%s",
            (relation, kind),
        ).fetchall()
        if not constraints:
            pytest.fail("missing_database_constraint:" + relation + ":" + kind, pytrace=False)


def activity(connection, **changes):
    values = dict(
        id=uuid4(),
        slug="synthetic-" + uuid4().hex,
        title="Synthetic activity",
        description="Synthetic plain text\nSecond line",
        duration_minutes=60,
        timezone="Europe/Vienna",
        is_active=True,
    )
    values.update(changes)
    connection.execute(
        "INSERT INTO public.activities "
        "(id,slug,title,description,duration_minutes,timezone,is_active) "
        "VALUES (%(id)s,%(slug)s,%(title)s,%(description)s,%(duration_minutes)s,%(timezone)s,"
        "%(is_active)s)",
        values,
    )
    return values["id"]


def booking(connection, activity_id, **changes):
    values = dict(
        id=uuid4(),
        activity_id=activity_id,
        starts_at=START,
        ends_at=START + timedelta(hours=1),
        status="confirmed",
        canceled_at=None,
    )
    values.update(changes)
    connection.execute(
        "INSERT INTO public.bookings (id,activity_id,starts_at,ends_at,status,canceled_at) "
        "VALUES (%(id)s,%(activity_id)s,%(starts_at)s,%(ends_at)s,%(status)s,%(canceled_at)s)",
        values,
    )
    return values["id"]


def window(connection, activity_id, start=time(9), end=time(10), weekday=1):
    connection.execute(
        "INSERT INTO public.weekly_windows "
        "(id,activity_id,iso_weekday,start_local_time,end_local_time) VALUES (%s,%s,%s,%s,%s)",
        (uuid4(), activity_id, weekday, start, end),
    )


@pytest.mark.parametrize("duration", [0, -15, 16])
def test_activity_duration_has_a_stable_database_check(pg_database, duration):
    with pg_database.connection() as connection:
        require_relations(connection, "public.activities")
        with rejected(connection, "23514"):
            activity(connection, duration_minutes=duration)


def test_activity_slug_is_unique(pg_database):
    with pg_database.connection() as connection:
        require_relations(connection, "public.activities")
        activity(connection, slug="synthetic-duplicate")
        with rejected(connection, "23505"):
            activity(connection, slug="synthetic-duplicate")


@pytest.mark.parametrize("weekday", [0, 8])
def test_weekday_range_is_enforced(pg_database, weekday):
    with pg_database.connection() as connection:
        require_relations(connection, "public.activities", "public.weekly_windows")
        identifier = activity(connection)
        with rejected(connection, "23514"):
            window(connection, identifier, weekday=weekday)


@pytest.mark.parametrize(
    "start,end", [(time(9), time(9)), (time(10), time(9)), (time(23), time(1))]
)
def test_empty_reversed_and_overnight_windows_are_rejected(pg_database, start, end):
    with pg_database.connection() as connection:
        require_relations(connection, "public.activities", "public.weekly_windows")
        identifier = activity(connection)
        with rejected(connection, "23514"):
            window(connection, identifier, start, end)


@pytest.mark.parametrize("start,end", [(time(9), time(10)), (time(9, 30), time(10, 30))])
def test_duplicate_and_overlapping_windows_are_rejected(pg_database, start, end):
    with pg_database.connection() as connection:
        require_relations(connection, "public.activities", "public.weekly_windows")
        identifier = activity(connection)
        window(connection, identifier)
        with rejected(connection, "23505", "23P01"):
            window(connection, identifier, start, end)


def test_touching_fractional_windows_stay_distinct_and_activity_weekday_scoped(pg_database):
    with pg_database.connection() as connection:
        require_relations(connection, "public.activities", "public.weekly_windows")
        identifier = activity(connection)
        boundary = time(9, 0, 0, 500000)
        window(connection, identifier, time(9), boundary)
        window(connection, identifier, boundary, time(10))
        window(connection, identifier, time(9), boundary, weekday=2)
        window(connection, activity(connection), time(9), boundary)
        assert connection.execute("SELECT count(*) FROM public.weekly_windows").fetchone() == (4,)
        assert connection.execute(
            "SELECT end_local_time FROM public.weekly_windows "
            "WHERE activity_id=%s AND iso_weekday=1 ORDER BY start_local_time",
            (identifier,),
        ).fetchall() == [(boundary,), (time(10),)]


def test_blocked_date_composite_key_is_per_activity(pg_database):
    with pg_database.connection() as connection:
        require_relations(connection, "public.activities", "public.blocked_dates")
        first, second = activity(connection), activity(connection)
        insert = "INSERT INTO public.blocked_dates (activity_id,local_date) VALUES (%s,%s)"
        connection.execute(insert, (first, START.date()))
        connection.execute(insert, (second, START.date()))
        with rejected(connection, "23505"):
            connection.execute(insert, (first, START.date()))


@pytest.mark.parametrize("child", ["weekly_windows", "blocked_dates", "bookings"])
def test_activity_foreign_keys_are_restrict_and_cannot_cascade_history(pg_database, child):
    with pg_database.connection() as connection:
        require_relations(connection, "public.activities", "public." + child)
        identifier = activity(connection)
        if child == "weekly_windows":
            window(connection, identifier)
        elif child == "blocked_dates":
            connection.execute(
                "INSERT INTO public.blocked_dates (activity_id,local_date) VALUES (%s,%s)",
                (identifier, START.date()),
            )
        else:
            booking(connection, identifier)
        actions = connection.execute(
            "SELECT confdeltype FROM pg_constraint WHERE contype='f' "
            "AND conrelid=to_regclass(%s) AND confrelid='public.activities'::regclass",
            ("public." + child,),
        ).fetchall()
        assert actions and all(action == ("r",) for action in actions)
        with rejected(connection, "23503"):
            connection.execute("DELETE FROM public.activities WHERE id=%s", (identifier,))
        assert connection.execute("SELECT count(*) FROM public.activities").fetchone() == (1,)
        assert connection.execute(
            "SELECT count(*) FROM " + "public." + child,
        ).fetchone() == (1,)


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"ends_at": START}, "23514"),
        ({"ends_at": START - timedelta(seconds=1)}, "23514"),
        ({"status": "invalid"}, "23514"),
        ({"canceled_at": START}, "23514"),
        ({"status": "canceled"}, "23514"),
        ({"starts_at": None}, "23502"),
        ({"ends_at": None}, "23502"),
    ],
    ids=[
        "equal",
        "reversed",
        "status",
        "confirmed-with-cancel",
        "canceled-without-time",
        "null-start",
        "null-end",
    ],
)
def test_booking_stable_checks_and_not_null_are_enforced(pg_database, changes, code):
    with pg_database.connection() as connection:
        require_relations(connection, "public.activities", "public.bookings")
        identifier = activity(connection)
        with rejected(connection, code):
            booking(connection, identifier, **changes)


def test_confirmed_overlap_uses_named_gist_exclusion(pg_database):
    with pg_database.connection() as connection:
        require_relations(connection, "public.activities", "public.bookings")
        identifier = activity(connection)
        booking(connection, identifier)
        with pytest.raises(psycopg.Error) as error, connection.transaction():
            booking(
                connection,
                identifier,
                starts_at=START + timedelta(minutes=30),
                ends_at=START + timedelta(minutes=90),
            )
        assert error.value.sqlstate == "23P01"
        assert error.value.diag.constraint_name == "no_overlap_confirmed"
        assert connection.execute(
            "SELECT am.amname,i.indisvalid FROM pg_constraint c "
            "JOIN pg_index i ON i.indexrelid=c.conindid "
            "JOIN pg_class idx ON idx.oid=i.indexrelid JOIN pg_am am ON am.oid=idx.relam "
            "WHERE c.conrelid='public.bookings'::regclass AND c.contype='x' "
            "AND c.conname='no_overlap_confirmed'"
        ).fetchone() == ("gist", True)


def test_adjacent_canceled_and_other_activity_intervals_are_allowed(pg_database):
    with pg_database.connection() as connection:
        require_relations(connection, "public.activities", "public.bookings")
        identifier = activity(connection)
        booking(connection, identifier)
        booking(
            connection,
            identifier,
            starts_at=START + timedelta(hours=1),
            ends_at=START + timedelta(hours=2),
        )
        booking(connection, identifier, status="canceled", canceled_at=START)
        booking(connection, activity(connection))
        assert connection.execute("SELECT count(*) FROM public.bookings").fetchone() == (4,)


@pytest.mark.concurrency
def test_simultaneous_confirmed_overlap_is_rejected_on_independent_connections(pg_database):
    with pg_database.connection() as seed:
        require_relations(seed, "public.activities", "public.bookings")
        identifier = activity(seed)
    ready = Queue()

    def contender():
        try:
            with pg_database.connection() as other:
                ready.put(other.execute("SELECT pg_backend_pid()").fetchone()[0])
                booking(other, identifier)
        except psycopg.Error as error:
            return error.sqlstate
        return "committed"

    with ThreadPoolExecutor(max_workers=1) as executor:
        with pg_database.connection() as winner:
            winner_pid = winner.execute("SELECT pg_backend_pid()").fetchone()[0]
            booking(winner, identifier)
            future = executor.submit(contender)
            other_pid = ready.get(timeout=5)
            assert other_pid != winner_pid
            deadline = monotonic() + 5
            with pg_database.connection() as observer:
                while True:
                    blockers = observer.execute(
                        "SELECT pg_blocking_pids(%s)", (other_pid,)
                    ).fetchone()[0]
                    if winner_pid in blockers:
                        break
                    assert not future.done(), "exclusion_did_not_wait_for_uncommitted_overlap"
                    assert monotonic() < deadline, "exclusion_lock_not_observed"
                    sleep(0.02)
        assert future.result(timeout=10) == "23P01"
    with pg_database.connection() as check:
        assert check.execute("SELECT count(*) FROM public.bookings").fetchone() == (1,)


def test_checks_use_no_current_time_or_cross_row_queries(pg_database):
    with pg_database.connection() as connection:
        require_relations(
            connection,
            "public.activities",
            "public.weekly_windows",
            "public.bookings",
            "private.booking_attempts",
        )
        checks = connection.execute(
            "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
            "JOIN pg_namespace n ON n.oid=c.connamespace "
            "WHERE c.contype='c' AND n.nspname IN ('public','private')"
        ).fetchall()
        assert checks
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
        for (definition,) in checks:
            assert not any(token in definition.lower() for token in forbidden)
