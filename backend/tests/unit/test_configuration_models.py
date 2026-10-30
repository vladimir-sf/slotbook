"""T011 mapped configuration validation; PostgreSQL enforces schedule invariants."""

import zoneinfo
from datetime import UTC, time

import pytest

from app.models import Activity, Base, BlockedDate, WeeklyWindow

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def packaged_timezone_environment(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    monkeypatch.setenv("PYTHONTZPATH", "")
    monkeypatch.setattr(zoneinfo, "TZPATH", ())


def test_registry_contains_the_three_configuration_mappings():
    for model, name in (
        (Activity, "activities"),
        (WeeklyWindow, "weekly_windows"),
        (BlockedDate, "blocked_dates"),
    ):
        assert Base.metadata.tables["public." + name] is model.__table__


@pytest.mark.parametrize(
    "padding",
    [chr(code) for code in range(0x110000) if chr(code).isspace()],
    ids=lambda _: "unicode-padding",
)
def test_description_trims_unicode_outer_whitespace_only(padding):
    value = "📘 Plain text\n  Literal <markup> & combining e\u0301"
    assert Activity(description=padding + value + padding).description == value


@pytest.mark.parametrize(
    "value",
    ["", "\u2003\t\n", "📘" * 2001, None, 1],
    ids=["empty", "blank", "too-long", "null", "wrong-type"],
)
def test_invalid_descriptions_fail_with_safe_codes(value):
    with pytest.raises(ValueError, match="^invalid_description$"):
        Activity(description=value)


def test_description_counts_codepoints_and_failed_assignment_preserves_previous_value():
    activity = Activity(description=" \U0001f4d8" * 1000 + "\t")
    # Internal spaces count; trimming removes only the initial outer space.
    assert len(activity.description) == 1999
    maximum = "\U0001f4d8" * 2000
    activity.description = "\u3000" + maximum + "\u3000"
    assert activity.description == maximum
    with pytest.raises(ValueError, match="^invalid_description$"):
        activity.description = maximum + "x"
    assert activity.description == maximum


def test_slug_and_title_keep_existing_unrestricted_string_semantics():
    activity = Activity(slug="", title=" Synthetic " * 500)
    assert activity.slug == ""
    assert activity.title == " Synthetic " * 500


@pytest.mark.parametrize("name", ["UTC", "Europe/Vienna", "Australia/Lord_Howe", "Pacific/Apia"])
def test_activity_timezone_loads_from_pinned_package(name):
    assert Activity(timezone=name).timezone == name


@pytest.mark.parametrize("name", ["Synthetic/Invalid", "../UTC", "/UTC", None])
def test_invalid_timezones_are_rejected(name):
    with pytest.raises(ValueError, match="^invalid_timezone$"):
        Activity(timezone=name)


@pytest.mark.parametrize("value", [time(9), time(9, 0, 0, 1), time(23, 59, 59, 999999)])
def test_local_clocks_keep_fractional_precision(value):
    window = WeeklyWindow(start_local_time=value, end_local_time=value)
    assert window.start_local_time is value
    assert window.end_local_time is value
    # Ordering/overlap is a database invariant, verified against PostgreSQL.


@pytest.mark.parametrize("value", [time(9, tzinfo=UTC), "09:00", None])
def test_local_clocks_reject_offsets_and_non_time_inputs(value):
    for attribute in ("start_local_time", "end_local_time"):
        with pytest.raises(ValueError, match="^invalid_local_clock$"):
            WeeklyWindow(**{attribute: value})
