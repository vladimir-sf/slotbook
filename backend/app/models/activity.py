"""T011 activity configuration; no booking history or API route behavior."""

from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base
from app.time import load_timezone

# Python 3.12 str.strip() whitespace, frozen into the stable database CHECK.
# U& escapes avoid database locale/regex differences for Unicode outer trim.
DESCRIPTION_CHECK = (
    "char_length(description) BETWEEN 1 AND 2000 AND description = btrim(description, "
    r"U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680"
    r"\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000')"
)


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("slug"),
        CheckConstraint(DESCRIPTION_CHECK, name="description_valid"),
        CheckConstraint(
            "duration_minutes > 0 AND duration_minutes % 15 = 0", name="duration_minutes_valid"
        ),
        {"schema": "public"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)

    @validates("description")
    def normalize_description(self, key: str, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("invalid_description")
        normalized = value.strip()
        if not 1 <= len(normalized) <= 2000:
            raise ValueError("invalid_description")
        return normalized

    @validates("timezone")
    def validate_timezone(self, key: str, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("invalid_timezone")
        # PostgreSQL/system timezone catalogs are not the pinned Python source.
        load_timezone(value)
        return value
