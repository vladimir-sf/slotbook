"""API v1 wire scalars, closed bodies and value-free validation guidance.

Instants/local clocks stay strings at the wire boundary to preserve arbitrary
fractional precision. Database conversion/eligibility belongs to later tasks.
No HTTP handlers, request logging or authentication are installed here (T016).
"""

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib import resources
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from email_validator import EmailNotValidError, validate_email
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    WithJsonSchema,
)

_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
_GENERATION = _UUID.replace("a-fA-F", "a-f")
_INSTANT = re.compile(
    r"(\d{4}-\d{2}-\d{2})[Tt](\d{2}:\d{2}:\d{2})(\.\d+)?([Zz]|[+-]\d{2}:\d{2})",
    re.ASCII,
)
_LOCAL_CLOCK = r"(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9](?:\.[0-9]+)?)?"


class Body(BaseModel):
    """Use contracted aliases exclusively; never coerce JSON primitive types."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
    )


def _id(value: str) -> str:
    if re.fullmatch(_UUID, value) is None:
        raise ValueError("invalid_uuid")
    return str(UUID(value))


def _email(value: str) -> str:
    try:
        # Validate syntax, then discard the validator's normalized identity.
        # Test domains, quoted locals and IP literals need no delivery lookup.
        validate_email(
            value,
            check_deliverability=False,
            test_environment=True,
            allow_quoted_local=True,
            allow_domain_literal=True,
        )
    except EmailNotValidError:
        raise ValueError("invalid_email") from None
    return value


def _name(value: str) -> str:
    if not value.strip():
        raise ValueError("invalid_attendee_name")
    return value


def _instant(value: object) -> str:
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise ValueError("aware_instant_required")
        value = value.isoformat()
    if not isinstance(value, str) or (match := _INSTANT.fullmatch(value)) is None:
        raise ValueError("invalid_aware_instant")
    day, clock, fraction, offset = match.groups()
    if offset not in ("Z", "z") and (int(offset[1:3]) > 23 or int(offset[4:]) > 59):
        raise ValueError("invalid_aware_instant")
    try:
        base = datetime.fromisoformat(f"{day}T{clock}{offset.upper()}").astimezone(UTC)
    except (ValueError, OverflowError):
        raise ValueError("invalid_aware_instant") from None
    suffix = (fraction or "").rstrip("0").rstrip(".")
    return base.replace(tzinfo=None).isoformat(timespec="seconds") + suffix + "Z"


def instant_order(value: str) -> tuple[datetime, Decimal]:
    """Compare validated UTC strings without losing sub-microsecond precision."""
    base, _, fraction = value.removesuffix("Z").partition(".")
    return datetime.fromisoformat(base), Decimal("0." + (fraction or "0"))


def _date(value: str) -> str:
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("invalid_date")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError("invalid_date") from None
    return value


def _timezone(value: str) -> str:
    parts = value.split("/")
    if any(part in ("", ".", "..") or "\\" in part for part in parts):
        raise ValueError("invalid_timezone")
    try:
        # Read only the locked package, independent of host TZPATH or caches.
        with resources.files("tzdata.zoneinfo").joinpath(*parts).open("rb") as source:
            ZoneInfo.from_file(source, key=value)
    except (OSError, ValueError):
        raise ValueError("invalid_timezone") from None
    return value


def _description(value: str) -> str:
    normalized = value.strip()
    if not 1 <= len(normalized) <= 2000:
        raise ValueError("invalid_description")
    return normalized


def _normalized_description(value: str) -> str:
    if value != value.strip() or not 1 <= len(value) <= 2000:
        raise ValueError("invalid_normalized_description")
    return value


def _local_clock(value: str) -> str:
    if re.fullmatch(_LOCAL_CLOCK, value, flags=re.ASCII) is None:
        raise ValueError("invalid_local_clock")
    return value


def local_clock_order(value: str) -> tuple[int, int, Decimal]:
    """Ordering of validated offset-free clocks, preserving all fraction digits."""
    hour, minute, *second = value.split(":")
    return int(hour), int(minute), Decimal(second[0] if second else "0")


type Id = Annotated[str, AfterValidator(_id), WithJsonSchema({"type": "string", "format": "uuid"})]
type Email = Annotated[
    str, AfterValidator(_email), WithJsonSchema({"type": "string", "format": "email"})
]
type AttendeeName = Annotated[str, Field(pattern=r"\S"), AfterValidator(_name)]
type UtcInstant = Annotated[
    str, BeforeValidator(_instant), WithJsonSchema({"type": "string", "format": "date-time"})
]
type LocalDate = Annotated[
    str, AfterValidator(_date), WithJsonSchema({"type": "string", "format": "date"})
]
type IanaTimezone = Annotated[str, AfterValidator(_timezone)]
type ActivityDescription = Annotated[str, AfterValidator(_description)]
type NormalizedActivityDescription = Annotated[
    str, Field(min_length=1, max_length=2000), AfterValidator(_normalized_description)
]
type LocalClock = Annotated[
    str, AfterValidator(_local_clock), Field(pattern="^" + _LOCAL_CLOCK + "$")
]
type ActivityDuration = Annotated[int, Field(ge=15, le=2**31 - 1, multiple_of=15)]
type AttemptGeneration = Annotated[str, Field(pattern="^" + _GENERATION + "$")]
type BookingAttemptKey = Annotated[
    str, Field(pattern="^" + _GENERATION + r"\.[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$")
]

type FieldCode = Literal["required", "invalid", "unknown_field", "overlap", "duplicate"]
type InputErrorCode = Literal[
    "validation_failed", "slug_conflict", "slot_ineligible", "notice_required", "horizon_exceeded"
]
type SafeErrorCode = Literal[
    "not_found",
    "internal_error",
    "service_unavailable",
    "unauthorized",
    "slot_unavailable",
    "attempt_mismatch",
    "attempt_invalidated_by_restore",
    "admission_unverified",
    "execution_unverified",
    "attempt_expired",
]


class FieldError(Body):
    path: str
    code: FieldCode
    message: str


class SafeError[Code: str](Body):
    code: Code
    message: str


class ApiError[Code: str](SafeError[Code]):
    fields: list[FieldError] = Field(default_factory=list)


type ValidationFailed = ApiError[Literal["validation_failed"]]
type InputError = ApiError[InputErrorCode]
type CommonError = SafeError[SafeErrorCode]


class HealthStatus(Body):
    status: Literal["ok"]


class ReadyStatus(Body):
    status: Literal["ready"]


_PATH_PARTS = frozenset(
    {
        "slug",
        "title",
        "description",
        "durationMinutes",
        "timezone",
        "isActive",
        "id",
        "activityId",
        "startsAt",
        "endsAt",
        "attendeeName",
        "attendeeEmail",
        "isoWeekday",
        "localStart",
        "localEnd",
        "date",
        "email",
        "password",
        "contact",
        "state",
        "status",
        "canceledAt",
        "accessToken",
        "tokenType",
        "expiresAt",
        "generation",
        "displayTimezone",
    }
)
_FIELD_MESSAGES: dict[FieldCode, str] = {
    "required": "This field is required.",
    "invalid": "This field is invalid.",
    "unknown_field": "Unknown fields are not allowed.",
    "overlap": "Windows must not overlap.",
    "duplicate": "Duplicate windows are not allowed.",
}


def validation_failed(error: ValidationError) -> ValidationFailed:
    """Project only fixed codes/messages and allowlisted paths; never raw input/ctx."""
    fields: list[FieldError] = []
    for issue in error.errors(include_input=False, include_url=False, include_context=False):
        code: FieldCode = "invalid"
        if issue["type"] == "extra_forbidden":
            code = "unknown_field"
        elif issue["type"] == "missing":
            code = "required"
        parts = [part for part in issue["loc"] if part not in ("present", "removed")]
        known = all((isinstance(part, int) and part >= 0) or part in _PATH_PARTS for part in parts)
        path = ".".join(str(part) for part in parts) if known and code != "unknown_field" else "$"
        fields.append(FieldError(path=path or "$", code=code, message=_FIELD_MESSAGES[code]))
    return ApiError[Literal["validation_failed"]](
        code="validation_failed", message="Request validation failed.", fields=fields
    )


class BodyValidationError(ValueError):
    """Safe boundary exception; callers serialize body, never a raw framework error."""

    def __init__(self, body: ValidationFailed) -> None:
        super().__init__("validation_failed")
        self.body = body


def parse_body[T](adapter: TypeAdapter[T], payload: str | bytes) -> T:
    """Validate model/array/union JSON and expose only the contracted safe error."""
    try:
        return adapter.validate_json(payload, strict=True)
    except ValidationError as error:
        raise BodyValidationError(validation_failed(error)) from None
