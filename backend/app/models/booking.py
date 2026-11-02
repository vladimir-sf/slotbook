"""T012 contact-free retained history; database guards own persistent immutability."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base
from app.time import as_utc


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="interval_valid"),
        CheckConstraint("status IN ('confirmed', 'canceled')", name="status_valid"),
        CheckConstraint(
            "(status = 'confirmed' AND canceled_at IS NULL) OR "
            "(status = 'canceled' AND canceled_at IS NOT NULL)",
            name="cancellation_consistent",
        ),
        ExcludeConstraint(
            ("activity_id", "="),
            (text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            where=text("status = 'confirmed'"),
            using="gist",
            name="no_overlap_confirmed",
        ),
        {"schema": "public"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    activity_id: Mapped[UUID] = mapped_column(
        ForeignKey("public.activities.id", ondelete="RESTRICT"), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @validates("starts_at", "ends_at", "canceled_at")
    def validate_instant(self, key: str, value: object) -> datetime | None:
        if key == "canceled_at" and value is None:
            return None
        if not isinstance(value, datetime):
            raise ValueError("invalid_booking_instant")
        return as_utc(value)
