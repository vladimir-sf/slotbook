"""Public contact-free booking results and the protected contact discriminator."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.common import (
    AttendeeName,
    AttemptGeneration,
    Body,
    Email,
    Id,
    UtcInstant,
    instant_order,
)


class Slot(Body):
    starts_at: UtcInstant = Field(alias="startsAt")
    ends_at: UtcInstant = Field(alias="endsAt")

    @model_validator(mode="after")
    def ordered(self) -> Slot:
        if instant_order(self.ends_at) <= instant_order(self.starts_at):
            raise ValueError("interval_end_must_follow_start")
        return self


class BookingRequest(Body):
    activity_id: Id = Field(alias="activityId")
    starts_at: UtcInstant = Field(alias="startsAt")
    attendee_name: AttendeeName = Field(alias="attendeeName", repr=False)
    attendee_email: Email = Field(alias="attendeeEmail", repr=False)


class BookingSummary(Slot):
    id: Id
    activity_id: Id = Field(alias="activityId")
    status: Literal["confirmed", "canceled"]
    canceled_at: UtcInstant | None = Field(alias="canceledAt")

    @model_validator(mode="after")
    def cancellation_state(self) -> BookingSummary:
        if (self.status == "confirmed") != (self.canceled_at is None):
            raise ValueError("invalid_cancellation_state")
        return self


class PresentContacts(Body):
    state: Literal["present"]
    attendee_name: AttendeeName = Field(alias="attendeeName", repr=False)
    attendee_email: Email = Field(alias="attendeeEmail", repr=False)


class RemovedContacts(Body):
    state: Literal["removed"]


type BookingContact = Annotated[PresentContacts | RemovedContacts, Field(discriminator="state")]


class AdminBooking(BookingSummary):
    # The caller must perform retention/read suppression before creating this body.
    contact: BookingContact = Field(repr=False)


class AttemptContext(Body):
    generation: AttemptGeneration


class AttemptPending(Body):
    state: Literal["pending"]
    expires_at: UtcInstant = Field(alias="expiresAt")
