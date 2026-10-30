"""T014 verifier-only storage and UTC model tests; no login or seed behavior."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pwdlib import PasswordHash

from app.models import Admin, AdminSession, WorkerStatus

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def encoded_hash():
    return PasswordHash.recommended().hash(uuid4().hex)


def test_models_have_no_raw_password_token_or_contact_columns():
    assert set(Admin.__table__.columns.keys()) == {"id", "email", "password_hash"}
    assert set(AdminSession.__table__.columns.keys()) == {
        "token_digest",
        "admin_id",
        "issued_at",
        "expires_at",
    }
    assert set(WorkerStatus.__table__.columns.keys()) == {
        "id",
        "last_heartbeat",
        "last_successful_purge",
        "overdue_count",
        "safe_failure_code",
    }
    with pytest.raises(TypeError):
        Admin(password=uuid4().hex)
    with pytest.raises(TypeError):
        AdminSession(token=uuid4().hex)


def test_pinned_argon2_hash_is_accepted(encoded_hash):
    assert Admin(password_hash=encoded_hash).password_hash == encoded_hash


@pytest.mark.parametrize("value", ["synthetic-not-a-hash", "a" * 64, None])
def test_plaintext_and_fast_digest_are_not_admin_hashes(value):
    with pytest.raises(ValueError, match="^invalid_admin_hash$"):
        Admin(password_hash=value)


def test_weak_work_factors_are_rejected(encoded_hash):
    from argon2 import extract_parameters

    parameters = extract_parameters(encoded_hash)
    weak = encoded_hash.replace("m=" + str(parameters.memory_cost), "m=8")
    with pytest.raises(ValueError, match="^invalid_admin_hash$"):
        Admin(password_hash=weak)


@pytest.mark.parametrize(
    "model,field",
    [
        (AdminSession, "issued_at"),
        (AdminSession, "expires_at"),
        (WorkerStatus, "last_heartbeat"),
        (WorkerStatus, "last_successful_purge"),
    ],
)
def test_security_operational_instants_are_aware_utc(model, field):
    supplied = datetime(2030, 1, 1, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert getattr(model(**{field: supplied}), field) == supplied.astimezone(UTC)
    with pytest.raises(ValueError, match="aware_instant_required"):
        model(**{field: supplied.replace(tzinfo=None)})


def test_worker_timestamps_may_be_unknown_before_first_success():
    status = WorkerStatus(last_heartbeat=None, last_successful_purge=None)
    assert status.last_heartbeat is None and status.last_successful_purge is None
