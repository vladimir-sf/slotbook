"""T012 immutable six-field history, partial exclusion and isolated contacts.

No attempt/auth/worker schemas, retention service, API routes or backup CLI.
Historical DDL is self-contained and contains no contact values or credentials.
"""

import sqlalchemy as sa
from alembic import op
from alembic.util import CommandError
from sqlalchemy.dialects import postgresql

revision = "0003_bookings"
down_revision = "0002_configuration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bookings")),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["public.activities.id"],
            ondelete="RESTRICT",
            name=op.f("fk_bookings_activity_id_activities"),
        ),
        sa.CheckConstraint("starts_at < ends_at", name=op.f("ck_bookings_interval_valid")),
        sa.CheckConstraint(
            "status IN ('confirmed', 'canceled')", name=op.f("ck_bookings_status_valid")
        ),
        sa.CheckConstraint(
            "(status = 'confirmed' AND canceled_at IS NULL) OR "
            "(status = 'canceled' AND canceled_at IS NOT NULL)",
            name=op.f("ck_bookings_cancellation_consistent"),
        ),
        postgresql.ExcludeConstraint(
            ("activity_id", "="),
            (sa.text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            where=sa.text("status = 'confirmed'"),
            using="gist",
            name="no_overlap_confirmed",
        ),
        schema="public",
    )
    # CHECKs cannot compare OLD/NEW. This invoker trigger protects retained values
    # even for direct SQL by the migration owner; no SECURITY DEFINER or data query.
    op.execute("""
        CREATE FUNCTION private.preserve_booking_history() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        BEGIN
          IF NEW.id IS DISTINCT FROM OLD.id OR
             NEW.activity_id IS DISTINCT FROM OLD.activity_id OR
             NEW.starts_at IS DISTINCT FROM OLD.starts_at OR
             NEW.ends_at IS DISTINCT FROM OLD.ends_at OR
             (OLD.status = 'canceled' AND
               (NEW.status IS DISTINCT FROM OLD.status OR
                NEW.canceled_at IS DISTINCT FROM OLD.canceled_at)) THEN
            RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'booking_history_immutable';
          END IF;
          RETURN NEW;
        END $$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION private.preserve_booking_history() "
        "FROM PUBLIC, slotbook_runtime, slotbook_backup"
    )
    op.execute(
        "CREATE TRIGGER preserve_booking_history BEFORE UPDATE ON public.bookings "
        "FOR EACH ROW EXECUTE FUNCTION private.preserve_booking_history()"
    )
    op.create_table(
        "booking_contacts",
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendee_name", sa.Text(), nullable=False),
        sa.Column("attendee_email", sa.Text(), nullable=False),
        sa.Column("delete_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("booking_id", name=op.f("pk_booking_contacts")),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["public.bookings.id"],
            ondelete="RESTRICT",
            name=op.f("fk_booking_contacts_booking_id_bookings"),
        ),
        schema="private",
    )
    op.create_index(
        op.f("ix_booking_contacts_delete_at"), "booking_contacts", ["delete_at"], schema="private"
    )
    op.execute(
        "REVOKE ALL ON public.bookings, private.booking_contacts "
        "FROM PUBLIC, slotbook_runtime, slotbook_backup"
    )
    op.execute("GRANT SELECT, INSERT ON public.bookings TO slotbook_runtime")
    op.execute("GRANT UPDATE (status, canceled_at) ON public.bookings TO slotbook_runtime")
    op.execute("GRANT SELECT, INSERT, DELETE ON private.booking_contacts TO slotbook_runtime")
    op.execute("GRANT UPDATE (delete_at) ON private.booking_contacts TO slotbook_runtime")
    # Do not grant table SELECT: future columns must never enter this allowlist.
    op.execute(
        "GRANT SELECT (id, activity_id, starts_at, ends_at, status, canceled_at) "
        "ON public.bookings TO slotbook_backup"
    )


def downgrade() -> None:
    raise CommandError("database_downgrade_requires_reviewed_operator_procedure")
