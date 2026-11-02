"""T013 mapping/UTC regression; commit and expiry guarantees use PostgreSQL."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.models import AttemptBinding, Base, BookingAttempt, RecoveryEvent, RetryGeneration

pytestmark = pytest.mark.unit
FIELDS = [
    (BookingAttempt, "first_received_at"),
    (BookingAttempt, "expires_at"),
    (RetryGeneration, "created_at"),
    (RecoveryEvent, "restored_at"),
]


def test_private_registry_has_only_digest_binding_and_safe_recovery_fields():
    for model in (BookingAttempt, AttemptBinding, RetryGeneration, RecoveryEvent):
        assert Base.metadata.tables["private." + model.__tablename__] is model.__table__
        assert not {
            "raw_key",
            "attendee_name",
            "attendee_email",
            "payload",
            "transaction_id",
        } & set(model.__table__.columns.keys())
    assert list(BookingAttempt.__table__.primary_key.columns.keys()) == ["generation", "key_digest"]
    assert list(AttemptBinding.__table__.primary_key.columns.keys()) == ["generation", "key_digest"]


@pytest.mark.parametrize("model,field", FIELDS)
def test_attempt_recovery_instants_are_utc(model, field):
    instant = datetime(2030, 1, 1, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert getattr(model(**{field: instant}), field) == instant.astimezone(UTC)


@pytest.mark.parametrize("model,field", FIELDS)
def test_attempt_recovery_instants_cannot_be_naive(model, field):
    with pytest.raises(ValueError, match="aware_instant_required"):
        model(**{field: datetime(2030, 1, 1)})
