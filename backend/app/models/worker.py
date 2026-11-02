"""T014 operational status only; no worker process, contacts or credential state."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base
from app.time import as_utc


class WorkerStatus(Base):
    __tablename__ = "worker_status"
    __table_args__ = (
        CheckConstraint("id=1", name="singleton"),
        CheckConstraint("overdue_count>=0", name="overdue_count_valid"),
        CheckConstraint(
            "safe_failure_code IS NULL OR safe_failure_code IN "
            "('worker_not_started','database_unavailable','cleanup_failed','lock_timeout')",
            name="failure_code_safe",
        ),
        {"schema": "private"},
    )
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_purge: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    overdue_count: Mapped[int] = mapped_column(Integer, nullable=False)
    safe_failure_code: Mapped[str | None] = mapped_column(Text)

    @validates("last_heartbeat", "last_successful_purge")
    def validate_instant(self, key: str, value: datetime | None) -> datetime | None:
        return None if value is None else as_utc(value)
