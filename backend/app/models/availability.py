"""T011 activity-local windows and blocked dates, independent of bookings."""

from datetime import date, time
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, SmallInteger, text
from sqlalchemy.dialects.postgresql import TIME, ExcludeConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base

WINDOW_CHECK = (
    "end_local_time > start_local_time AND "
    "start_local_time < TIME '24:00:00' AND end_local_time < TIME '24:00:00'"
)
# EXTRACT on PostgreSQL time returns exact numeric seconds, not floating point.
# Keep microseconds and [) bounds; no minute rounding, merging or date/DST guess.
WINDOW_RANGE = (
    "numrange(EXTRACT(EPOCH FROM start_local_time) * 1000000, "
    "EXTRACT(EPOCH FROM end_local_time) * 1000000, '[)')"
)


class WeeklyWindow(Base):
    __tablename__ = "weekly_windows"
    __table_args__ = (
        CheckConstraint("iso_weekday BETWEEN 1 AND 7", name="iso_weekday_valid"),
        CheckConstraint(WINDOW_CHECK, name="local_window_valid"),
        ExcludeConstraint(
            ("activity_id", "="),
            ("iso_weekday", "="),
            (text(WINDOW_RANGE), "&&"),
            name="no_overlap_weekly_windows",
            using="gist",
        ),
        {"schema": "public"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    activity_id: Mapped[UUID] = mapped_column(
        ForeignKey("public.activities.id", ondelete="RESTRICT"), nullable=False
    )
    iso_weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_local_time: Mapped[time] = mapped_column(
        TIME(timezone=False, precision=6), nullable=False
    )
    end_local_time: Mapped[time] = mapped_column(TIME(timezone=False, precision=6), nullable=False)

    @validates("start_local_time", "end_local_time")
    def validate_local_clock(self, key: str, value: object) -> time:
        if not isinstance(value, time) or value.tzinfo is not None:
            raise ValueError("invalid_local_clock")
        return value


class BlockedDate(Base):
    __tablename__ = "blocked_dates"
    __table_args__ = {"schema": "public"}

    activity_id: Mapped[UUID] = mapped_column(
        ForeignKey("public.activities.id", ondelete="RESTRICT"), primary_key=True
    )
    local_date: Mapped[date] = mapped_column(Date, primary_key=True)
