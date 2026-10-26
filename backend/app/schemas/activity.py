"""Frozen API v1 activity and schedule bodies; no persistence or route behavior."""

from __future__ import annotations

from pydantic import Field, model_validator

from app.schemas.common import (
    ActivityDescription,
    ActivityDuration,
    Body,
    IanaTimezone,
    Id,
    LocalClock,
    LocalDate,
    NormalizedActivityDescription,
    local_clock_order,
)


class ActivityWrite(Body):
    slug: str
    title: str
    description: ActivityDescription
    duration_minutes: ActivityDuration = Field(alias="durationMinutes")
    timezone: IanaTimezone
    is_active: bool = Field(alias="isActive")


class Activity(ActivityWrite):
    description: NormalizedActivityDescription
    id: Id


class WeeklyWindow(Body):
    iso_weekday: int = Field(alias="isoWeekday", ge=1, le=7)
    local_start: LocalClock = Field(alias="localStart")
    local_end: LocalClock = Field(alias="localEnd")

    @model_validator(mode="after")
    def ordered(self) -> WeeklyWindow:
        if local_clock_order(self.local_end) <= local_clock_order(self.local_start):
            raise ValueError("window_end_must_follow_start")
        return self


class BlockedDate(Body):
    date: LocalDate
