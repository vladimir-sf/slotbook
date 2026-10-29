"""T018 unit/controlled-time evidence; real DB-clock proof is recorded separately.

These cases do not prove commit durability, admission, booking concurrency or
RP-01–17. T002 fixture contracts continue to run unchanged as doctests.
"""

import json
import os
import tempfile
import zoneinfo
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from threading import Event
from unittest.mock import Mock

import pytest
import tzdata
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError

from app import time as time_primitives
from app.time import (
    DatabaseClock,
    DatabaseClockError,
    TimezoneDataError,
    as_utc,
    deadline_reached,
    elapsed_after,
    load_timezone,
    local_instants,
    timezone_versions,
    to_local,
)
from tests.support.clock import Clock, FileClock, FrozenClock

pytestmark = [pytest.mark.unit, pytest.mark.timezone]
INSTANT = datetime(2030, 1, 1, tzinfo=UTC)
INSTANT_ISO = INSTANT.isoformat()
CASE = "synthetic-time-case"


@pytest.fixture(autouse=True)
def packaged_timezone_environment(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    monkeypatch.setenv("PYTHONTZPATH", "")
    monkeypatch.setattr(zoneinfo, "TZPATH", ())


@pytest.mark.parametrize("offset", [-345, 0, 60, 345, 660], ids=lambda _: "case")
def test_offsets_normalize_to_the_same_utc_instant(offset):
    zoned = INSTANT.astimezone(timezone(timedelta(minutes=offset)))
    assert as_utc(zoned) == INSTANT
    assert as_utc(zoned).tzinfo is UTC


def test_naive_instants_are_rejected():
    naive = INSTANT.replace(tzinfo=None)
    for action in (
        lambda: as_utc(naive),
        lambda: elapsed_after(naive, timedelta(hours=1)),
        lambda: deadline_reached(naive, INSTANT),
        lambda: to_local(naive, "UTC"),
    ):
        with pytest.raises(ValueError, match="aware_instant_required"):
            action()


@pytest.mark.parametrize(
    "local", [datetime(2026, 3, 28, 12), datetime(2026, 10, 24, 12)], ids=lambda _: "case"
)
def test_elapsed_day_across_dst_is_exactly_24_hours_in_utc(local):
    anchor = local.replace(tzinfo=load_timezone("Europe/Vienna"))
    deadline = elapsed_after(anchor, timedelta(hours=24))
    assert deadline.tzinfo is UTC
    assert deadline - as_utc(anchor) == timedelta(hours=24)
    assert deadline.astimezone(anchor.tzinfo).hour != anchor.hour


@pytest.mark.parametrize(
    "elapsed",
    [
        timedelta(hours=1),
        timedelta(hours=24),
        timedelta(minutes=60),
        timedelta(hours=720),
        timedelta(hours=1440),
    ],
    ids=lambda _: "case",
)
@pytest.mark.parametrize("step,due", [(-1, False), (0, True), (1, True)], ids=lambda _: "case")
def test_controlled_elapsed_boundaries_before_equal_after(elapsed, step, due):
    # Controlled arithmetic only: no claim that an admission/worker/session exists.
    clock = FrozenClock(INSTANT)
    deadline = elapsed_after(clock.now(), elapsed)
    clock.set(deadline + timedelta(microseconds=step))
    assert deadline_reached(clock.now(), deadline) is due
    assert deadline - INSTANT == elapsed


def test_same_zone_fold_comparisons_are_ordered_by_instant():
    zone = load_timezone("Europe/Vienna")
    earlier = datetime(2026, 10, 25, 2, 45, tzinfo=zone, fold=0)
    later = datetime(2026, 10, 25, 2, 15, tzinfo=zone, fold=1)
    assert deadline_reached(later, earlier)
    assert not deadline_reached(earlier, later)


@pytest.mark.parametrize(
    "label,name,expected",
    [
        (datetime(2026, 3, 29, 2, 30), "Europe/Vienna", ()),
        (
            datetime(2026, 10, 25, 2, 30),
            "Europe/Vienna",
            ("2026-10-25T00:30:00+00:00", "2026-10-25T01:30:00+00:00"),
        ),
        (datetime(2026, 10, 4, 2, 15), "Australia/Lord_Howe", ()),
        (
            datetime(2026, 4, 5, 1, 45),
            "Australia/Lord_Howe",
            ("2026-04-04T14:45:00+00:00", "2026-04-04T15:15:00+00:00"),
        ),
        (datetime(2011, 12, 30, 12), "Pacific/Apia", ()),
        (
            datetime(2030, 1, 1, 9, 10, 15, 123456),
            "Europe/Vienna",
            ("2030-01-01T08:10:15.123456+00:00",),
        ),
    ],
    ids=lambda _: "case",
)
def test_iana_round_trips_keep_both_folds_and_never_shift_gaps(label, name, expected):
    actual = local_instants(label, name)
    assert tuple(value.isoformat() for value in actual) == expected
    assert all(value.tzinfo is UTC for value in actual)
    assert all(to_local(value, name).replace(tzinfo=None) == label for value in actual)
    if len(actual) == 2:
        labels = [to_local(value, name) for value in actual]
        assert labels[0].utcoffset() != labels[1].utcoffset()
        assert [value.fold for value in labels] == [0, 1]


def test_local_ordinary_label_deduplicates_and_aware_label_is_not_reinterpreted():
    label = INSTANT.replace(tzinfo=None)
    assert local_instants(label, "UTC") == (INSTANT,)
    with pytest.raises(ValueError, match="local_label_must_be_naive"):
        local_instants(INSTANT, "UTC")
    assert to_local(INSTANT, "Asia/Kathmandu").utcoffset() == timedelta(hours=5, minutes=45)


def test_exact_locked_timezone_versions_and_package_source():
    assert timezone_versions() == {
        "tzdata": "2026.5",
        "iana": "2026e",
        "timezone_source": "tzdata",
    }


@pytest.mark.parametrize(
    "setting,value",
    [("TZ", "Europe/Vienna"), ("PYTHONTZPATH", "/usr/share/zoneinfo"), ("PYTHONTZPATH", None)],
    ids=lambda _: "case",
)
def test_invalid_timezone_environment_fails_instead_of_reconfiguring(setting, value, monkeypatch):
    if value is None:
        monkeypatch.delenv(setting)
    else:
        monkeypatch.setenv(setting, value)
    with pytest.raises(TimezoneDataError, match="timezone_configuration_invalid"):
        timezone_versions()


def test_nonempty_runtime_tzpath_fails_even_with_empty_environment(monkeypatch):
    monkeypatch.setattr(zoneinfo, "TZPATH", ("/synthetic-host-timezones",))
    with pytest.raises(TimezoneDataError, match="timezone_configuration_invalid"):
        load_timezone("UTC")


def test_package_metadata_and_lock_must_agree(monkeypatch):
    monkeypatch.setattr(time_primitives.metadata, "version", lambda _: "wrong-version")
    with pytest.raises(TimezoneDataError, match="timezone_data_version_invalid"):
        timezone_versions()


def test_iana_version_is_required(monkeypatch):
    monkeypatch.setattr(tzdata, "IANA_VERSION", None)
    with pytest.raises(TimezoneDataError, match="timezone_data_version_invalid"):
        timezone_versions()


def test_missing_lock_or_package_fails_closed(monkeypatch):
    read_text = Path.read_text

    def unavailable(path, *args, **kwargs):
        if path.name == "requirements.lock":
            raise FileNotFoundError("synthetic_private_path")
        return read_text(path, *args, **kwargs)

    with monkeypatch.context() as inner:
        inner.setattr(Path, "read_text", unavailable)
        with pytest.raises(TimezoneDataError, match="^timezone_data_unavailable$"):
            timezone_versions()
    monkeypatch.setattr(time_primitives, "import_module", Mock(side_effect=ModuleNotFoundError()))
    with pytest.raises(TimezoneDataError, match="^timezone_data_unavailable$"):
        timezone_versions()


@pytest.mark.parametrize("contents", [None, b"not-a-tzif"], ids=lambda _: "case")
def test_missing_or_corrupt_packaged_data_does_not_fall_back(tmp_path, monkeypatch, contents):
    if contents is not None:
        (tmp_path / "UTC").write_bytes(contents)
    monkeypatch.setattr(time_primitives.resources, "files", lambda _: tmp_path)
    with pytest.raises(TimezoneDataError, match="^timezone_data_unavailable$"):
        load_timezone("UTC")


def test_named_zone_cache_is_never_used(monkeypatch):
    original = zoneinfo.ZoneInfo
    keys = []

    class CacheTrap:
        def __new__(cls, *args, **kwargs):
            raise AssertionError("named_zone_cache_used")

        @staticmethod
        def from_file(source, *, key):
            keys.append(key)
            return original.from_file(source, key=key)

    monkeypatch.setattr(zoneinfo, "ZoneInfo", CacheTrap)
    assert load_timezone("Europe/Vienna").key == "Europe/Vienna"
    assert keys == ["UTC", "Europe/Vienna"]


@pytest.mark.parametrize(
    "zone",
    ["Invalid/Synthetic", "../UTC", "/UTC", "Europe//Vienna", "UTC\\bad"],
    ids=lambda _: "case",
)
def test_invalid_named_zones_are_rejected(zone):
    with pytest.raises(ValueError, match="invalid_timezone"):
        load_timezone(zone)


def test_database_clock_unit_samples_fresh_after_a_wait_and_normalizes_offset():
    connection = Mock(spec=Connection)
    result = connection.execute.return_value
    first = INSTANT.astimezone(timezone(timedelta(hours=2)))
    second = first + timedelta(seconds=1)
    result.scalar_one.side_effect = [first, second]
    clock = DatabaseClock(connection)
    assert connection.execute.call_count == 0
    assert clock.now() == INSTANT
    ready = Event()
    ready.set()
    assert ready.wait(timeout=1)
    assert clock.now() == INSTANT + timedelta(seconds=1)
    assert connection.execute.call_count == 2
    for call in connection.execute.call_args_list:
        sql = str(call.args[0].compile(dialect=postgresql.dialect()))
        assert "clock_timestamp()" in sql
        assert "CURRENT_TIMESTAMP" not in sql and "now()" not in sql


@pytest.mark.parametrize(
    "value", [None, "2030-01-01T00:00:00Z", INSTANT.replace(tzinfo=None)], ids=lambda _: "case"
)
def test_database_clock_rejects_invalid_results_without_host_fallback(value):
    connection = Mock(spec=Connection)
    connection.execute.return_value.scalar_one.return_value = value
    with pytest.raises(DatabaseClockError, match="^database_clock_invalid_instant$"):
        DatabaseClock(connection).now()


def test_database_clock_failure_is_value_free_and_no_host_fallback():
    connection = Mock(spec=Connection)
    connection.execute.side_effect = OperationalError(
        "synthetic_private_sql", {}, Exception("synthetic_private")
    )
    with pytest.raises(DatabaseClockError) as caught:
        DatabaseClock(connection).now()
    assert str(caught.value) == "database_clock_unavailable"
    assert "synthetic_private" not in str(caught.value) + repr(caught.value)


def write_control(directory: Path, *, instant=INSTANT_ISO, case_id=CASE):
    with tempfile.NamedTemporaryFile(dir=directory, mode="w", delete=False) as output:
        json.dump({"caseId": case_id, "instant": instant}, output)
        temporary = Path(output.name)
    os.replace(temporary, directory / "clock.json")


def test_controlled_file_clock_shared_injections_reread_each_sample(private_runtime_dir):
    write_control(private_runtime_dir, instant="2030-01-01T02:00:00+02:00")
    with FileClock(private_runtime_dir, case_id=CASE) as server:
        with FileClock(private_runtime_dir, case_id=CASE) as worker:
            typed_clock: Clock = server
            assert typed_clock.now() == worker.now() == INSTANT
            next_instant = INSTANT + timedelta(hours=24, microseconds=1)
            write_control(private_runtime_dir, instant=next_instant.isoformat())
            assert server.now() == worker.now() == next_instant


def test_controlled_file_clock_cross_process_uses_existing_private_subprocess_fixture(
    private_runtime_dir,
    python_subprocess,
):
    write_control(private_runtime_dir)
    backend = Path(__file__).resolve().parents[2]
    code = (
        f"import sys; sys.path.insert(0, {str(backend)!r}); "
        "from pathlib import Path; from tests.support.clock import FileClock; "
        f"clock=FileClock(Path.cwd(),case_id={CASE!r}); "
        "print(clock.now().isoformat()); clock.close()"
    )
    child = python_subprocess.start(code)
    assert child.wait(timeout=5) == 0, "controlled_clock_child_failed"
    assert (private_runtime_dir / "child-0.stdout").read_text().strip() == INSTANT.isoformat()


@pytest.mark.parametrize(
    "contents",
    [
        b"{",
        b"[]",
        b"null",
        b"\xff",
        b'{"caseId":"wrong-case","instant":"2030-01-01T00:00:00Z"}',
        b'{"caseId":"synthetic-time-case","instant":"2030-01-01T00:00:00"}',
        b'{"caseId":"synthetic-time-case","instant":123}',
        b'{"caseId":"synthetic-time-case","instant":"2030-01-01T00:00:00+00:60"}',
        b'{"caseId":"synthetic-time-case","instant":"2030-01-01T00:00:00.0000001Z"}',
        b'{"caseId":"synthetic-time-case","instant":"0001-01-01T00:00:00+23:59"}',
        b'{"caseId":"synthetic-time-case","instant":"9999-12-31T23:59:59-23:59"}',
        b'{"caseId":"synthetic-time-case","instant":"2030-01-01T00:00:00Z","body":"synthetic_private"}',
        b'{"caseId":"synthetic-time-case","caseId":"synthetic-time-case","instant":"2030-01-01T00:00:00Z"}',
        b" " * 4097,
    ],
    ids=lambda _: "case",
)
def test_controlled_file_clock_invalid_data_is_safe_and_never_uses_host_time(
    private_runtime_dir, contents
):
    file = private_runtime_dir / "clock.json"
    with file.open("wb") as output:
        output.write(contents)
    file.chmod(0o600)
    with FileClock(private_runtime_dir, case_id=CASE) as clock:
        with pytest.raises(ValueError) as caught:
            clock.now()
        assert str(caught.value) == "fixture_clock_control_invalid"


def test_controlled_file_clock_requires_private_permissions_and_regular_single_link_file(
    private_runtime_dir,
):
    write_control(private_runtime_dir)
    file = private_runtime_dir / "clock.json"
    with FileClock(private_runtime_dir, case_id=CASE) as clock:
        file.chmod(0o644)
        with pytest.raises(ValueError, match="control_invalid"):
            clock.now()
        file.chmod(0o600)
        (private_runtime_dir / "extra-link").hardlink_to(file)
        with pytest.raises(ValueError, match="control_invalid"):
            clock.now()
        (private_runtime_dir / "extra-link").unlink()
        private_runtime_dir.chmod(0o755)
        with pytest.raises(ValueError, match="control_invalid"):
            clock.now()
    with pytest.raises(ValueError, match="control_invalid"):
        FileClock(private_runtime_dir, case_id=CASE)


def test_controlled_file_clock_rejects_symlinks_missing_files_and_fifo(
    private_runtime_dir, tmp_path
):
    alias = tmp_path / "alias"
    alias.symlink_to(private_runtime_dir, target_is_directory=True)
    with pytest.raises(ValueError, match="control_unavailable"):
        FileClock(alias, case_id=CASE)
    with FileClock(private_runtime_dir, case_id=CASE) as clock:
        with pytest.raises(ValueError, match="control_unavailable"):
            clock.now()
        file = private_runtime_dir / "clock.json"
        file.symlink_to(tmp_path / "missing")
        with pytest.raises(ValueError, match="control_unavailable"):
            clock.now()
        file.unlink()
        os.mkfifo(file, mode=0o600)
        with pytest.raises(ValueError, match="control_invalid"):
            clock.now()


def test_controlled_file_clock_directory_identity_is_pinned_and_close_is_idempotent(
    private_runtime_dir,
):
    write_control(private_runtime_dir)
    with FileClock(private_runtime_dir, case_id=CASE) as clock:
        moved = private_runtime_dir.with_name("moved-private-runtime")
        private_runtime_dir.rename(moved)
        private_runtime_dir.mkdir(mode=0o700)
        write_control(private_runtime_dir, instant=(INSTANT + timedelta(days=1)).isoformat())
        assert clock.now() == INSTANT
    clock.close()
    with pytest.raises(RuntimeError, match="control_closed"):
        clock.now()


@pytest.mark.parametrize(
    "case_id", ["", "../case", "case@example.org", "x" * 65], ids=lambda _: "case"
)
def test_controlled_file_clock_case_identifier_is_not_a_payload_or_path(
    private_runtime_dir, case_id
):
    with pytest.raises(ValueError, match="^fixture_clock_control_invalid$"):
        FileClock(private_runtime_dir, case_id=case_id)


def test_controlled_file_clock_requires_current_owner(private_runtime_dir, monkeypatch):
    write_control(private_runtime_dir)
    uid = os.geteuid()
    monkeypatch.setattr(os, "geteuid", lambda: uid + 1)
    with pytest.raises(ValueError, match="^fixture_clock_control_invalid$"):
        FileClock(private_runtime_dir, case_id=CASE)


def test_production_time_import_never_discovers_test_control(python_subprocess):
    backend = Path(__file__).resolve().parents[2]
    code = (
        f"import sys,os; sys.path.insert(0, {str(backend)!r}); "
        "os.environ['SLOTBOOK_TEST_CONTROL_DIR']='synthetic_unapproved_control'; "
        "import app.time; assert not any(n.startswith('tests.support') for n in sys.modules)"
    )
    child = python_subprocess.start(code)
    assert child.wait(timeout=5) == 0, "production_time_control_isolation_failed"
