"""T013 atomic private admission, immutable receipts and non-authorizing expiry."""

import sqlalchemy as sa
from alembic import op
from alembic.util import CommandError
from sqlalchemy.dialects import postgresql as pg

revision = "0004_attempts"
down_revision = "0003_bookings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
      CREATE FUNCTION private.safe_attempt_fields(value jsonb) RETURNS boolean
      LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
        SELECT CASE WHEN jsonb_typeof(value)='array' THEN NOT EXISTS (
          SELECT 1 FROM jsonb_array_elements(value) item WHERE jsonb_typeof(item)<>'object'
          OR item - 'path' - 'code' <> '{}'::jsonb
          OR NOT (item ? 'path' AND item ? 'code')
          OR coalesce(item->>'path','') NOT IN
             ('body','activityId','startsAt','attendeeName','attendeeEmail')
          OR coalesce(item->>'code','') NOT IN
             ('required','invalid','unknown_field','overlap','duplicate')
        ) ELSE false END
      $$
    """)
    op.create_table(
        "booking_attempts",
        sa.Column("generation", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("key_digest", sa.LargeBinary(), nullable=False),
        sa.Column("first_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("booking_id", pg.UUID(as_uuid=True)),
        sa.Column("rejection_status", sa.Integer()),
        sa.Column("rejection_code", sa.Text()),
        sa.Column("rejection_fields", pg.JSONB(none_as_null=True)),
        sa.PrimaryKeyConstraint("generation", "key_digest", name=op.f("pk_booking_attempts")),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["public.bookings.id"],
            ondelete="RESTRICT",
            name=op.f("fk_booking_attempts_booking_id_bookings"),
        ),
        sa.CheckConstraint(
            "octet_length(key_digest)=32", name=op.f("ck_booking_attempts_key_digest_valid")
        ),
        sa.CheckConstraint(
            "expires_at - first_received_at = INTERVAL '24 hours'",
            name=op.f("ck_booking_attempts_receipt_valid"),
        ),
        sa.CheckConstraint(
            "state IN ('admitted','succeeded','rejected','expired')",
            name=op.f("ck_booking_attempts_state_valid"),
        ),
        sa.CheckConstraint(
            "(state IN ('admitted','expired') AND booking_id IS NULL AND rejection_status IS NULL "
            "AND rejection_code IS NULL AND rejection_fields IS NULL) OR "
            "(state='succeeded' AND booking_id IS NOT NULL AND rejection_status IS NULL "
            "AND rejection_code IS NULL AND rejection_fields IS NULL) OR "
            "(state='rejected' AND booking_id IS NULL AND "
            "((rejection_status=400 AND rejection_code IN "
            "('validation_failed','slot_ineligible','notice_required','horizon_exceeded')) OR "
            "(rejection_status=409 AND rejection_code='slot_unavailable')) "
            "AND rejection_status IS NOT NULL AND rejection_code IS NOT NULL)",
            name=op.f("ck_booking_attempts_result_consistent"),
        ),
        sa.CheckConstraint(
            "rejection_fields IS NULL OR private.safe_attempt_fields(rejection_fields)",
            name=op.f("ck_booking_attempts_fields_safe"),
        ),
        schema="private",
    )
    op.create_index(
        op.f("ix_booking_attempts_expires_at"), "booking_attempts", ["expires_at"], schema="private"
    )
    op.create_table(
        "attempt_bindings",
        sa.Column("generation", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("key_digest", sa.LargeBinary(), nullable=False),
        sa.Column("payload_fingerprint", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("generation", "key_digest", name=op.f("pk_attempt_bindings")),
        sa.ForeignKeyConstraint(
            ["generation", "key_digest"],
            ["private.booking_attempts.generation", "private.booking_attempts.key_digest"],
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
            name=op.f("fk_attempt_bindings_generation_booking_attempts"),
        ),
        sa.CheckConstraint(
            "payload_fingerprint ~ '^v[1-9][0-9]*:[0-9a-f]{64}$'",
            name=op.f("ck_attempt_bindings_fingerprint_valid"),
        ),
        schema="private",
    )
    op.execute("""
      CREATE FUNCTION private.guard_attempt_update() RETURNS trigger
      LANGUAGE plpgsql SET search_path=pg_catalog AS $$
      BEGIN
        IF (NEW.generation,NEW.key_digest,NEW.first_received_at,NEW.expires_at)
             IS DISTINCT FROM
             (OLD.generation,OLD.key_digest,OLD.first_received_at,OLD.expires_at) OR
           (OLD.state='expired' AND NEW.state<>'expired') OR
           (OLD.state IN ('succeeded','rejected') AND NEW.state<>'expired' AND
             (NEW.state,NEW.booking_id,NEW.rejection_status,NEW.rejection_code,NEW.rejection_fields)
             IS DISTINCT FROM
             (OLD.state,OLD.booking_id,OLD.rejection_status,
              OLD.rejection_code,OLD.rejection_fields)) THEN
          RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='attempt_state_immutable';
        END IF;
        IF NEW.state='expired' THEN
          DELETE FROM private.attempt_bindings WHERE generation=OLD.generation
            AND key_digest=OLD.key_digest;
          NEW.booking_id:=NULL; NEW.rejection_status:=NULL;
          NEW.rejection_code:=NULL; NEW.rejection_fields:=NULL;
        END IF;
        RETURN NEW;
      END $$
    """)
    op.execute(
        "CREATE TRIGGER guard_attempt_update BEFORE UPDATE ON private.booking_attempts "
        "FOR EACH ROW EXECUTE FUNCTION private.guard_attempt_update()"
    )
    # Claim binding first (deferred FK), then INSERT the final sampled T/E late.
    # Receipt values never change after insertion; no transaction metadata is used.
    op.execute("""
      CREATE FUNCTION private.check_attempt_receipt() RETURNS trigger
      LANGUAGE plpgsql SET search_path=pg_catalog AS $$
      DECLARE current_row private.booking_attempts;
      BEGIN
        SELECT * INTO current_row FROM private.booking_attempts
          WHERE generation=NEW.generation AND key_digest=NEW.key_digest;
        IF TG_OP='INSERT' THEN
          IF FOUND AND current_row.state<>'expired' AND NOT EXISTS (
            SELECT 1 FROM private.attempt_bindings
              WHERE generation=NEW.generation AND key_digest=NEW.key_digest) THEN
            RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='attempt_binding_required';
          END IF;
        END IF;
        RETURN NULL;
      END $$
    """)
    op.execute(
        "CREATE CONSTRAINT TRIGGER check_attempt_receipt AFTER INSERT ON "
        "private.booking_attempts DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
        "EXECUTE FUNCTION private.check_attempt_receipt()"
    )
    op.execute("""
      CREATE FUNCTION private.guard_attempt_binding() RETURNS trigger
      LANGUAGE plpgsql SET search_path=pg_catalog AS $$
      BEGIN
        IF TG_OP='UPDATE' THEN
          IF NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='attempt_binding_immutable';
          END IF;
          RETURN NEW;
        END IF;
        IF EXISTS (SELECT 1 FROM private.attempt_bindings
                   WHERE generation=NEW.generation AND key_digest=NEW.key_digest)
           AND EXISTS (SELECT 1 FROM private.booking_attempts WHERE generation=NEW.generation
                       AND key_digest=NEW.key_digest AND state='expired') THEN
          RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='expired_attempt_binding_forbidden';
        END IF;
        RETURN NULL;
      END $$
    """)
    op.execute(
        "CREATE TRIGGER guard_binding_update BEFORE UPDATE ON private.attempt_bindings "
        "FOR EACH ROW EXECUTE FUNCTION private.guard_attempt_binding()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER check_binding_state AFTER INSERT ON private.attempt_bindings "
        "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
        "EXECUTE FUNCTION private.guard_attempt_binding()"
    )
    op.create_table(
        "retry_generation",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("generation", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retry_generation")),
        sa.UniqueConstraint("generation", name=op.f("uq_retry_generation_generation")),
        sa.CheckConstraint("id=1", name=op.f("ck_retry_generation_singleton")),
        schema="private",
    )
    op.create_table(
        "recovery_events",
        sa.Column(
            "id", pg.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_reference", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("old_generation", pg.UUID(as_uuid=True)),
        sa.Column("new_generation", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("state_loss_reason", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recovery_events")),
        sa.CheckConstraint(
            "old_generation IS NULL OR old_generation<>new_generation",
            name=op.f("ck_recovery_events_epoch_changed"),
        ),
        sa.CheckConstraint(
            "state_loss_reason='qualified_unrecoverable_restore'",
            name=op.f("ck_recovery_events_reason_safe"),
        ),
        schema="private",
    )
    for function in (
        "safe_attempt_fields(jsonb)",
        "guard_attempt_update()",
        "check_attempt_receipt()",
        "guard_attempt_binding()",
    ):
        op.execute(
            f"REVOKE ALL ON FUNCTION private.{function} "
            "FROM PUBLIC, slotbook_runtime, slotbook_backup"
        )
    op.execute("GRANT EXECUTE ON FUNCTION private.safe_attempt_fields(jsonb) TO slotbook_runtime")
    op.execute(
        "REVOKE ALL ON private.booking_attempts, private.attempt_bindings, "
        "private.retry_generation, "
        "private.recovery_events FROM PUBLIC, slotbook_runtime, slotbook_backup"
    )
    op.execute(
        "GRANT SELECT, INSERT ON private.booking_attempts, private.attempt_bindings, "
        "private.retry_generation TO slotbook_runtime"
    )
    op.execute("GRANT SELECT ON private.recovery_events TO slotbook_runtime")
    op.execute(
        "GRANT UPDATE (first_received_at,expires_at,state,booking_id,rejection_status,"
        "rejection_code,rejection_fields) "
        "ON private.booking_attempts TO slotbook_runtime"
    )
    op.execute("GRANT DELETE ON private.attempt_bindings TO slotbook_runtime")


def downgrade() -> None:
    raise CommandError("database_downgrade_requires_reviewed_operator_procedure")
