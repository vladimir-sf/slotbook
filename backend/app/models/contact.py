"""T012 ephemeral contacts; never a column, relationship cascade or copy in history.

The stored indexed deadline is an aid, not authority to extend retention. Booking
creation/cancellation must supply recorded end/original cancellation +720 elapsed
hours; the later worker/read services enforce that policy with authoritative time.
No name/email normalization, length limits or retained contact identifiers are added.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base
from app.time import as_utc


class BookingContact(Base):
    __tablename__ = "booking_contacts"
    __table_args__ = {"schema": "private"}

    booking_id: Mapped[UUID] = mapped_column(
        ForeignKey("public.bookings.id", ondelete="RESTRICT"), primary_key=True
    )
    attendee_name: Mapped[str] = mapped_column(Text, nullable=False)
    attendee_email: Mapped[str] = mapped_column(Text, nullable=False)
    delete_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    @validates("delete_at")
    def validate_deadline(self, key: str, value: object) -> datetime:
        if not isinstance(value, datetime):
            raise ValueError("invalid_contact_deadline")
        return as_utc(value)
