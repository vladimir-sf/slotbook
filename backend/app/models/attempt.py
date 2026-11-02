"""T013 private admission ledger; no raw keys, payloads or contact values."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    LargeBinary,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base
from app.time import as_utc

RESULT_CHECK = (
    "(state IN ('admitted','expired') AND booking_id IS NULL AND rejection_status IS NULL "
    "AND rejection_code IS NULL AND rejection_fields IS NULL) OR "
    "(state='succeeded' AND booking_id IS NOT NULL AND rejection_status IS NULL "
    "AND rejection_code IS NULL AND rejection_fields IS NULL) OR "
    "(state='rejected' AND booking_id IS NULL AND "
    "((rejection_status=400 AND rejection_code IN "
    "('validation_failed','slot_ineligible','notice_required','horizon_exceeded')) OR "
    "(rejection_status=409 AND rejection_code='slot_unavailable')) "
    "AND rejection_status IS NOT NULL AND rejection_code IS NOT NULL)"
)


class BookingAttempt(Base):
    __tablename__ = "booking_attempts"
    __table_args__ = (
        CheckConstraint("octet_length(key_digest)=32", name="key_digest_valid"),
        CheckConstraint(
            "expires_at - first_received_at = INTERVAL '24 hours'", name="receipt_valid"
        ),
        CheckConstraint(
            "state IN ('admitted','succeeded','rejected','expired')", name="state_valid"
        ),
        CheckConstraint(RESULT_CHECK, name="result_consistent"),
        CheckConstraint(
            "rejection_fields IS NULL OR private.safe_attempt_fields(rejection_fields)",
            name="fields_safe",
        ),
        {"schema": "private"},
    )

    generation: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    key_digest: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    first_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(Text, nullable=False)
    booking_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("public.bookings.id", ondelete="RESTRICT")
    )
    rejection_status: Mapped[int | None]
    rejection_code: Mapped[str | None] = mapped_column(Text)
    rejection_fields: Mapped[list[dict[str, str]] | None] = mapped_column(JSONB(none_as_null=True))

    @validates("first_received_at", "expires_at")
    def validate_instant(self, key: str, value: datetime) -> datetime:
        return as_utc(value)


class AttemptBinding(Base):
    __tablename__ = "attempt_bindings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["generation", "key_digest"],
            ["private.booking_attempts.generation", "private.booking_attempts.key_digest"],
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        # Version tag and digest share the approved fingerprint field, no raw body.
        CheckConstraint(
            "payload_fingerprint ~ '^v[1-9][0-9]*:[0-9a-f]{64}$'", name="fingerprint_valid"
        ),
        {"schema": "private"},
    )

    generation: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    key_digest: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    payload_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
