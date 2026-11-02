"""T013 restore epoch and privacy-safe operator metadata; no automatic rotation."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, SmallInteger, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base
from app.time import as_utc


class RetryGeneration(Base):
    __tablename__ = "retry_generation"
    __table_args__ = (
        CheckConstraint("id=1", name="singleton"),
        UniqueConstraint("generation"),
        {"schema": "private"},
    )
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    generation: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @validates("created_at")
    def validate_instant(self, key: str, value: datetime) -> datetime:
        return as_utc(value)


class RecoveryEvent(Base):
    __tablename__ = "recovery_events"
    __table_args__ = (
        CheckConstraint(
            "old_generation IS NULL OR old_generation<>new_generation", name="epoch_changed"
        ),
        CheckConstraint("state_loss_reason='qualified_unrecoverable_restore'", name="reason_safe"),
        {"schema": "private"},
    )
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    restored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_reference: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    old_generation: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    new_generation: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    state_loss_reason: Mapped[str] = mapped_column(Text, nullable=False)

    @validates("restored_at")
    def validate_instant(self, key: str, value: datetime) -> datetime:
        return as_utc(value)
