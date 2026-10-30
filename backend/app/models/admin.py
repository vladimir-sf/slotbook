"""T014 singleton admin and digest-only absolute sessions; no auth/seed service."""

from datetime import datetime
from uuid import UUID

from argon2 import extract_parameters
from argon2.exceptions import InvalidHashError
from argon2.low_level import Type
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, Text, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base
from app.time import as_utc


class Admin(Base):
    __tablename__ = "admins"
    __table_args__ = (
        Index("one_admin", text("(true)"), unique=True),
        CheckConstraint("private.secure_admin_hash(password_hash)", name="hash_valid"),
        {"schema": "private"},
    )
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    @validates("password_hash")
    def validate_hash(self, key: str, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("invalid_admin_hash")
        try:
            parameters = extract_parameters(value)
        except (InvalidHashError, ValueError):
            raise ValueError("invalid_admin_hash") from None
        if (
            parameters.type is not Type.ID
            or parameters.version != 19
            or not 19456 <= parameters.memory_cost <= 1048576
            or not 2 <= parameters.time_cost <= 10
            or not 1 <= parameters.parallelism <= 16
            or parameters.salt_len < 16
            or parameters.hash_len < 32
        ):
            raise ValueError("invalid_admin_hash")
        return value


class AdminSession(Base):
    __tablename__ = "admin_sessions"
    __table_args__ = (
        CheckConstraint("octet_length(token_digest)=32", name="digest_valid"),
        CheckConstraint("expires_at-issued_at=INTERVAL '60 minutes'", name="expiry_valid"),
        {"schema": "private"},
    )
    token_digest: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    admin_id: Mapped[UUID] = mapped_column(
        ForeignKey("private.admins.id", ondelete="RESTRICT"), nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    @validates("issued_at", "expires_at")
    def validate_instant(self, key: str, value: datetime) -> datetime:
        return as_utc(value)
