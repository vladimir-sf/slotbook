"""T012 mapping/instant tests; persistent constraints are tested on PostgreSQL."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.models import Base, Booking, BookingContact

pytestmark = pytest.mark.unit
INSTANT = datetime(2030, 1, 1, tzinfo=UTC)
FIELDS = [
    (Booking, "starts_at"),
    (Booking, "ends_at"),
    (Booking, "canceled_at"),
    (BookingContact, "delete_at"),
]


def test_history_and_contact_mappings_have_exactly_the_approved_separate_columns():
    assert Base.metadata.tables["public.bookings"] is Booking.__table__
    assert Base.metadata.tables["private.booking_contacts"] is BookingContact.__table__
    assert set(Booking.__table__.columns.keys()) == {
        "id",
        "activity_id",
        "starts_at",
        "ends_at",
        "status",
        "canceled_at",
    }
    assert set(BookingContact.__table__.columns.keys()) == {
        "booking_id",
        "attendee_name",
        "attendee_email",
        "delete_at",
    }
    with pytest.raises(TypeError):
        Booking(attendee_name="Synthetic")


@pytest.mark.parametrize("model,attribute", FIELDS)
@pytest.mark.parametrize("offset", [-300, 0, 330])
def test_instants_normalize_to_utc(model, attribute, offset):
    supplied = INSTANT.astimezone(timezone(timedelta(minutes=offset)))
    record = model(**{attribute: supplied})
    value = getattr(record, attribute)
    assert value == INSTANT and value.tzinfo is UTC


@pytest.mark.parametrize("model,attribute", FIELDS)
def test_naive_instants_fail_without_echoing_inputs(model, attribute):
    with pytest.raises(ValueError, match="^aware_instant_required$"):
        model(**{attribute: INSTANT.replace(tzinfo=None)})


@pytest.mark.parametrize("model,attribute", FIELDS)
def test_wrong_instant_types_are_rejected(model, attribute):
    with pytest.raises(ValueError, match="^invalid_(booking_instant|contact_deadline)$"):
        model(**{attribute: "synthetic-invalid-instant"})


def test_only_canceled_at_is_nullable():
    assert Booking(canceled_at=None).canceled_at is None
    assert Booking.__table__.c.canceled_at.nullable
    for table in (Booking.__table__, BookingContact.__table__):
        for column in table.columns:
            assert column.nullable == (table is Booking.__table__ and column.name == "canceled_at")


def test_contact_identity_is_preserved_without_normalization_or_extra_limits():
    name = " Synthetic  Attendee "
    email = "Synthetic.Local+Tag@example.invalid"
    record = BookingContact(attendee_name=name, attendee_email=email)
    assert record.attendee_name == name and record.attendee_email == email


def test_contact_deadline_has_an_index_and_foreign_key_cannot_cascade_to_history():
    table = BookingContact.__table__
    assert any(list(index.columns.keys()) == ["delete_at"] for index in table.indexes)
    foreign_key = next(iter(table.c.booking_id.foreign_keys))
    assert foreign_key.target_fullname == "public.bookings.id"
    assert foreign_key.ondelete == "RESTRICT"
