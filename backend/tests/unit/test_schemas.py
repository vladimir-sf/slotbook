"""T015 unit evidence for frozen API v1 bodies; no HTTP/DB feature claims."""

import json
from datetime import UTC, datetime
from typing import Literal

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.activity import Activity, ActivityWrite, BlockedDate, WeeklyWindow
from app.schemas.auth import AdminCredentials, AdminToken
from app.schemas.booking import (
    AdminBooking,
    AttemptContext,
    AttemptPending,
    BookingContact,
    BookingRequest,
    BookingSummary,
    PresentContacts,
    RemovedContacts,
    Slot,
)
from app.schemas.common import (
    ApiError,
    BodyValidationError,
    BookingAttemptKey,
    CommonError,
    Email,
    FieldError,
    HealthStatus,
    Id,
    InputError,
    LocalClock,
    ReadyStatus,
    SafeError,
    UtcInstant,
    parse_body,
)

pytestmark = pytest.mark.unit
ID = "123e4567-e89b-12d3-a456-426614174000"
START = "2030-01-01T10:00:00Z"
END = "2030-01-01T10:30:00Z"

# Private unit fixture captured from frozen API v1 adc0b83a; not a public DTO.
# Verified against the canonical OpenAPI before commit; independent of build context.
FROZEN_BODY_FIELDS = {
    "ActivityWrite": "description durationMinutes isActive slug timezone title",
    "Activity": "description durationMinutes id isActive slug timezone title",
    "WeeklyWindow": "isoWeekday localEnd localStart",
    "BlockedDate": "date",
    "BookingRequest": "activityId attendeeEmail attendeeName startsAt",
    "Slot": "endsAt startsAt",
    "BookingSummary": "activityId canceledAt endsAt id startsAt status",
    "PresentContacts": "attendeeEmail attendeeName state",
    "RemovedContacts": "state",
    "AdminBooking": "activityId canceledAt contact endsAt id startsAt status",
    "AttemptContext": "generation",
    "AttemptPending": "expiresAt state",
    "AdminCredentials": "email password",
    "AdminToken": "accessToken expiresAt tokenType",
    "FieldError": "code message path",
    "HealthStatus": "status",
    "ReadyStatus": "status",
}


def activity(**overrides):
    return dict(
        slug="synthetic",
        title="Synthetic activity",
        description="Description",
        durationMinutes=30,
        timezone="Europe/Vienna",
        isActive=True,
        **overrides,
    )


def request():
    return dict(
        activityId=ID,
        startsAt=START,
        attendeeName=" Synthetic Person ",
        attendeeEmail="Synthetic+Case@EXAMPLE.org",
    )


def summary():
    return dict(
        id=ID, activityId=ID, startsAt=START, endsAt=END, status="confirmed", canceledAt=None
    )


@pytest.mark.parametrize(
    "raw,normalized",
    [
        (" \t\nHello\u2003", "Hello"),
        ("\n<b>literal</b>\n  line two\n", "<b>literal</b>\n  line two"),
        (" 🦉 ", "🦉"),
        (" " * 3000 + "🦉" * 2000 + " " * 3000, "🦉" * 2000),
        ("e\u0301" * 1000, "e\u0301" * 1000),
    ],
    ids=lambda _: "case",
)
def test_description_preprocessing(raw, normalized):
    payload = activity()
    payload["description"] = raw
    assert ActivityWrite.model_validate(payload).description == normalized


@pytest.mark.parametrize(
    "bad", ["", " \u2003\n", "x" * 2001, "🦉" * 2001, None, 123], ids=lambda _: "case"
)
def test_invalid_description_rejected(bad):
    payload = activity()
    payload["description"] = bad
    with pytest.raises(ValidationError):
        ActivityWrite.model_validate(payload)


@pytest.mark.parametrize("description", [" x", "x ", " ", "x" * 2001], ids=lambda _: "case")
def test_read_description_must_already_be_canonical(description):
    payload = dict(activity(), id=ID)
    payload["description"] = description
    with pytest.raises(ValidationError):
        Activity.model_validate(payload)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("durationMinutes", 0),
        ("durationMinutes", -15),
        ("durationMinutes", 16),
        ("durationMinutes", True),
        ("durationMinutes", 30.0),
        ("durationMinutes", "30"),
        ("durationMinutes", 2**31),
        ("isActive", 1),
        ("isActive", "true"),
        ("slug", 2),
        ("title", None),
        ("timezone", "Invalid/Synthetic"),
        ("timezone", "../UTC"),
        ("timezone", "/UTC"),
        ("timezone", "Europe//Vienna"),
        ("timezone", "UTC\\bad"),
    ],
    ids=lambda _: "case",
)
def test_activity_strict_types_and_constraints(field, bad):
    payload = activity()
    payload[field] = bad
    with pytest.raises(ValidationError):
        ActivityWrite.model_validate(payload)


def test_no_unapproved_slug_title_or_identity_length_policy():
    payload = activity()
    payload.update(slug="", title="", durationMinutes=2147483640, timezone="UTC")
    assert ActivityWrite.model_validate(payload).slug == ""
    body = request()
    body["attendeeName"] = "🦉" * 10000
    assert BookingRequest.model_validate(body).attendee_name == body["attendeeName"]


@pytest.mark.parametrize(
    "value",
    [
        "Synthetic+Case@EXAMPLE.org",
        "é@example.org",
        '"a b"@example.org',
        "synthetic@example.test",
        "synthetic@[127.0.0.1]",
    ],
    ids=lambda _: "case",
)
def test_email_syntax_without_delivery_or_normalization(value):
    assert TypeAdapter(Email).validate_python(value, strict=True) == value


@pytest.mark.parametrize(
    "value",
    [
        "missing",
        "bad@@example.org",
        "a@",
        "@example.org",
        "a b@example.org",
        "Person <synthetic@example.org>",
        " synthetic@example.org",
        123,
        None,
    ],
    ids=lambda _: "case",
)
def test_invalid_email(value):
    with pytest.raises(ValidationError):
        TypeAdapter(Email).validate_python(value, strict=True)


def test_exact_identity_strings_and_public_privacy():
    body = BookingRequest.model_validate(request())
    assert body.attendee_name == request()["attendeeName"]
    assert body.attendee_email == request()["attendeeEmail"]
    assert body.model_dump() == request()
    assert "Synthetic Person" not in repr(body)
    public = BookingSummary.model_validate(summary()).model_dump(mode="json")
    assert set(public) == {"id", "activityId", "startsAt", "endsAt", "status", "canceledAt"}
    for key in ("attendeeName", "attendeeEmail", "contact", "accessToken", "idempotencyKey"):
        with pytest.raises(ValidationError):
            BookingSummary.model_validate(dict(summary(), **{key: "synthetic_private"}))


@pytest.mark.parametrize("name", ["", " \t\n\u2003", None, 123], ids=lambda _: "case")
def test_attendee_name_nonblank_without_trimming(name):
    body = request()
    body["attendeeName"] = name
    with pytest.raises(ValidationError):
        BookingRequest.model_validate(body)


def test_uuid_input_is_canonicalized_but_no_version_policy_is_added():
    assert TypeAdapter(Id).validate_python(ID.upper(), strict=True) == ID
    assert TypeAdapter(Id).validate_python("00000000-0000-0000-0000-000000000000")


@pytest.mark.parametrize(
    "value",
    [ID.replace("-", ""), "urn:uuid:" + ID, "{" + ID + "}", ID + "\n", "bad", 123, None],
    ids=lambda _: "case",
)
def test_uuid_invalid_format(value):
    with pytest.raises(ValidationError):
        TypeAdapter(Id).validate_python(value, strict=True)


@pytest.mark.parametrize(
    "raw,utc",
    [
        ("2030-01-01T11:00:00+01:00", START),
        ("2030-01-01T04:15:00-05:45", START),
        ("2030-01-01t10:00:00z", START),
        ("2030-01-01T11:00:00.123456789100+01:00", "2030-01-01T10:00:00.1234567891Z"),
        (datetime(2030, 1, 1, 10, tzinfo=UTC), START),
    ],
    ids=lambda _: "case",
)
def test_aware_instants_normalize_to_utc_without_rounding(raw, utc):
    assert TypeAdapter(UtcInstant).validate_python(raw, strict=True) == utc


@pytest.mark.parametrize(
    "value",
    [
        "2030-01-01T10:00:00",
        "2030-01-01",
        "2030-01-01 10:00:00Z",
        "2030-01-01T10:00:00+24:00",
        "2030-01-01T10:00:00+00:60",
        "2030-02-30T10:00:00Z",
        "123",
        123,
        123.0,
        None,
        datetime(2030, 1, 1, 10),
    ],
    ids=lambda _: "case",
)
def test_invalid_or_naive_instants_are_not_coerced(value):
    with pytest.raises(ValidationError):
        TypeAdapter(UtcInstant).validate_python(value, strict=True)


@pytest.mark.parametrize(
    "clock", ["00:00", "23:59", "09:10:15", "09:10:15.000000000000000001"], ids=lambda _: "case"
)
def test_local_clock_retains_unrestricted_fraction_precision(clock):
    assert TypeAdapter(LocalClock).validate_python(clock, strict=True) == clock


@pytest.mark.parametrize(
    "clock",
    [
        "9:00",
        "24:00",
        "12:60",
        "12:00:60",
        "12:00Z",
        "12:00+01:00",
        "12:00.1",
        "12:00:00.",
        " 12:00",
        "12:00\n",
        123,
    ],
    ids=lambda _: "case",
)
def test_invalid_local_clock(clock):
    with pytest.raises(ValidationError):
        TypeAdapter(LocalClock).validate_python(clock, strict=True)


def test_window_order_uses_exact_fractional_precision_and_accepts_touching():
    values = [
        dict(isoWeekday=1, localStart="09:10:00.0000000001", localEnd="09:10:00.0000000002"),
        dict(isoWeekday=1, localStart="09:10:00.0000000002", localEnd="10:00"),
    ]
    assert len(TypeAdapter(list[WeeklyWindow]).validate_python(values, strict=True)) == 2
    assert TypeAdapter(list[WeeklyWindow]).validate_python([], strict=True) == []


@pytest.mark.parametrize(
    "values",
    [
        dict(isoWeekday=0, localStart="09:00", localEnd="10:00"),
        dict(isoWeekday=8, localStart="09:00", localEnd="10:00"),
        dict(isoWeekday=True, localStart="09:00", localEnd="10:00"),
        dict(isoWeekday=1, localStart="09:00", localEnd="09:00:00.000"),
        dict(isoWeekday=1, localStart="23:00", localEnd="01:00"),
    ],
    ids=lambda _: "case",
)
def test_window_invalid_bounds(values):
    with pytest.raises(ValidationError):
        WeeklyWindow.model_validate(values)


@pytest.mark.parametrize(
    "value",
    ["2030-02-29", "2030-01-01T00:00:00Z", "20300101", "2030-1-1", 123],
    ids=lambda _: "case",
)
def test_blocked_date_has_no_instant_coercion(value):
    with pytest.raises(ValidationError):
        BlockedDate.model_validate({"date": value})


def test_valid_leap_date_and_utc_interval_serialization():
    assert BlockedDate.model_validate({"date": "2032-02-29"}).date == "2032-02-29"
    slot = Slot.model_validate({"startsAt": "2030-01-01T11:00:00+01:00", "endsAt": END})
    assert slot.model_dump(mode="json") == {"startsAt": START, "endsAt": END}
    tiny = Slot.model_validate(
        dict(startsAt="2030-01-01T10:00:00.0000000001Z", endsAt="2030-01-01T10:00:00.0000000002Z")
    )
    assert tiny.starts_at != tiny.ends_at
    with pytest.raises(ValidationError):
        Slot.model_validate(dict(startsAt=END, endsAt=START))


def test_required_nullable_cancellation_and_current_status():
    for status, cancellation in (("confirmed", START), ("canceled", None), ("unknown", None)):
        body = summary()
        body.update(status=status, canceledAt=cancellation)
        with pytest.raises(ValidationError):
            BookingSummary.model_validate(body)
    body = summary()
    del body["canceledAt"]
    with pytest.raises(ValidationError):
        BookingSummary.model_validate(body)
    body.update(status="canceled", canceledAt=END)
    assert BookingSummary.model_validate(body).canceled_at == END


@pytest.mark.parametrize(
    "contact",
    [
        {"state": "present", "attendeeName": "Synthetic", "attendeeEmail": "a@example.org"},
        {"state": "removed"},
    ],
    ids=lambda _: "case",
)
def test_discriminated_contact_union(contact):
    result = AdminBooking.model_validate(dict(summary(), contact=contact))
    assert result.model_dump(mode="json")["contact"] == contact


@pytest.mark.parametrize(
    "contact",
    [
        {},
        {"state": "unknown"},
        {"state": "present"},
        {"state": "removed", "attendeeName": None},
        {"state": "removed", "attendeeEmail": "fake@example.org"},
        {"state": "removed", "attendeeName": "placeholder", "attendeeEmail": "fake@example.org"},
    ],
    ids=lambda _: "case",
)
def test_contact_union_does_not_invent_null_or_placeholder_identities(contact):
    with pytest.raises(ValidationError):
        TypeAdapter(BookingContact).validate_python(contact, strict=True)


def bodies():
    return [
        (ActivityWrite, activity()),
        (Activity, dict(activity(), id=ID)),
        (WeeklyWindow, dict(isoWeekday=1, localStart="09:00", localEnd="10:00")),
        (BlockedDate, {"date": "2030-01-01"}),
        (BookingRequest, request()),
        (Slot, dict(startsAt=START, endsAt=END)),
        (BookingSummary, summary()),
        (
            PresentContacts,
            dict(state="present", attendeeName="Synthetic", attendeeEmail="a@example.org"),
        ),
        (RemovedContacts, dict(state="removed")),
        (AdminBooking, dict(summary(), contact={"state": "removed"})),
        (AttemptContext, dict(generation=ID)),
        (AttemptPending, dict(state="pending", expiresAt=START)),
        (AdminCredentials, dict(email="admin@example.org", password="")),
        (AdminToken, dict(accessToken="opaque-synthetic", tokenType="bearer", expiresAt=START)),
        (FieldError, dict(path="description", code="invalid", message="Invalid field.")),
        (HealthStatus, dict(status="ok")),
        (ReadyStatus, dict(status="ready")),
    ]


@pytest.mark.parametrize("schema,payload", bodies(), ids=lambda _: "case")
def test_all_closed_bodies_reject_unknown_fields(schema, payload):
    with pytest.raises(ValidationError):
        schema.model_validate(dict(payload, unknown="synthetic_private"))
    with pytest.raises(ValidationError):
        schema.model_validate({})


@pytest.mark.parametrize("schema,payload", bodies(), ids=lambda _: "case")
def test_wire_properties_and_required_fields_match_frozen_openapi_fixture(schema, payload):
    expected = set(FROZEN_BODY_FIELDS[schema.__name__].split())
    actual = schema.model_json_schema(by_alias=True)
    assert set(actual["properties"]) == expected
    assert set(actual["required"]) == expected
    assert actual["additionalProperties"] is False
    assert set(schema.model_validate_json(json.dumps(payload)).model_dump(mode="json")) == set(
        payload
    )


def test_python_field_names_are_not_extra_json_aliases():
    body = request()
    body["activity_id"] = body.pop("activityId")
    with pytest.raises(ValidationError):
        BookingRequest.model_validate_json(json.dumps(body))


def test_attempt_generation_and_key_are_canonical():
    key = ID + "." + "A" * 43
    assert TypeAdapter(BookingAttemptKey).validate_python(key, strict=True) == key
    for bad in (ID.upper() + "." + "A" * 43, key + "=", key[:-1] + "B", key + "\n", "digest"):
        with pytest.raises(ValidationError):
            TypeAdapter(BookingAttemptKey).validate_python(bad, strict=True)
    with pytest.raises(ValidationError):
        AttemptContext.model_validate({"generation": ID.upper()})


def test_safe_error_body_unions_reject_fields_and_uncontracted_codes():
    assert TypeAdapter(CommonError).validate_python(
        dict(code="attempt_mismatch", message="Mismatch.")
    )
    assert TypeAdapter(InputError).validate_python(
        dict(code="validation_failed", message="Invalid.")
    )
    with pytest.raises(ValidationError):
        TypeAdapter(CommonError).validate_python(
            dict(code="attempt_mismatch", message="Mismatch.", fields=[])
        )
    with pytest.raises(ValidationError):
        TypeAdapter(InputError).validate_python(dict(code="unapproved", message="Invalid."))
    with pytest.raises(ValidationError):
        ApiError[Literal["validation_failed"]].model_validate(
            dict(code="validation_failed", message="Invalid.", fields=None)
        )
    with pytest.raises(ValidationError):
        SafeError[Literal["internal_error"]].model_validate(
            dict(code="internal_error", message="Failed.", stack="synthetic_private")
        )


@pytest.mark.parametrize(
    "payload",
    [
        '{"attendeeEmail":"synthetic_private_invalid","synthetic_private_key":"synthetic_private_body"}',
        '{"attendeeEmail":"synthetic_private_invalid",',
        '"synthetic_private_body"',
    ],
    ids=lambda _: "case",
)
def test_validation_boundary_never_exposes_inputs_unknown_names_or_framework_details(payload):
    with pytest.raises(BodyValidationError) as caught:
        parse_body(TypeAdapter(BookingRequest), payload)
    safe = caught.value.body.model_dump_json()
    assert "synthetic_private" not in safe + str(caught.value) + repr(caught.value)
    assert set(json.loads(safe)) == {"code", "message", "fields"}
    assert all(set(field) == {"path", "code", "message"} for field in json.loads(safe)["fields"])
    assert "input" not in safe and "ctx" not in safe and "pydantic.dev" not in safe


def test_array_validation_paths_are_safe_and_unknown_names_always_use_root():
    payload = json.dumps(
        [
            dict(
                isoWeekday=8,
                localStart="09:00",
                localEnd="10:00",
                synthetic_private_name="synthetic_private_value",
            )
        ]
    )
    with pytest.raises(BodyValidationError) as caught:
        parse_body(TypeAdapter(list[WeeklyWindow]), payload)
    fields = caught.value.body.fields
    assert {(field.path, field.code) for field in fields} == {
        ("0.isoWeekday", "invalid"),
        ("$", "unknown_field"),
    }


def test_password_and_token_are_opaque_and_not_represented_in_model_repr():
    credentials = AdminCredentials.model_validate(
        dict(email="admin@example.org", password="synthetic_private")
    )
    token = AdminToken.model_validate(
        dict(accessToken="synthetic_private", tokenType="bearer", expiresAt=START)
    )
    assert "synthetic_private" not in repr(credentials) + repr(token)
    assert token.model_dump()["accessToken"] == "synthetic_private"
    with pytest.raises(ValidationError):
        AdminToken.model_validate(dict(accessToken="x", tokenType="Bearer", expiresAt=START))
