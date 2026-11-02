"""T014 private singleton admin, immutable verifier sessions and safe status."""

import sqlalchemy as sa
from alembic import op
from alembic.util import CommandError
from sqlalchemy.dialects import postgresql as pg

revision = "0005_security_worker"
down_revision = "0004_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PHC structure plus bounded Argon2id work factors; no raw password argument.
    op.execute(r"""
      CREATE FUNCTION private.secure_admin_hash(value text) RETURNS boolean
      LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
        SELECT CASE WHEN value ~
          '^\$argon2id\$v=19\$m=[0-9]{1,8},t=[0-9]{1,8},p=[0-9]{1,8}\$[A-Za-z0-9+/]{22,}\$[A-Za-z0-9+/]{43,}$'
        THEN substring(split_part(value,'$',4) FROM 'm=([0-9]+)')::integer BETWEEN 19456 AND 1048576
          AND substring(split_part(value,'$',4) FROM 't=([0-9]+)')::integer BETWEEN 2 AND 10
          AND substring(split_part(value,'$',4) FROM 'p=([0-9]+)')::integer BETWEEN 1 AND 16
        ELSE false END
      $$
    """)
    op.create_table(
        "admins",
        sa.Column(
            "id", pg.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admins")),
        sa.UniqueConstraint("email", name=op.f("uq_admins_email")),
        sa.CheckConstraint(
            "private.secure_admin_hash(password_hash)", name=op.f("ck_admins_hash_valid")
        ),
        schema="private",
    )
    op.create_index("one_admin", "admins", [sa.text("(true)")], unique=True, schema="private")
    op.create_table(
        "admin_sessions",
        sa.Column("token_digest", sa.LargeBinary(), nullable=False),
        sa.Column("admin_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("token_digest", name=op.f("pk_admin_sessions")),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["private.admins.id"],
            ondelete="RESTRICT",
            name=op.f("fk_admin_sessions_admin_id_admins"),
        ),
        sa.CheckConstraint(
            "octet_length(token_digest)=32", name=op.f("ck_admin_sessions_digest_valid")
        ),
        sa.CheckConstraint(
            "expires_at-issued_at=INTERVAL '60 minutes'",
            name=op.f("ck_admin_sessions_expiry_valid"),
        ),
        schema="private",
    )
    op.create_index(
        op.f("ix_admin_sessions_expires_at"), "admin_sessions", ["expires_at"], schema="private"
    )
    op.execute("""
      CREATE FUNCTION private.preserve_admin_session() RETURNS trigger
      LANGUAGE plpgsql SET search_path=pg_catalog AS $$
      BEGIN
        IF NEW IS DISTINCT FROM OLD THEN
          RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='admin_session_immutable';
        END IF;
        RETURN NEW;
      END $$
    """)
    op.execute(
        "CREATE TRIGGER preserve_admin_session BEFORE UPDATE ON private.admin_sessions "
        "FOR EACH ROW EXECUTE FUNCTION private.preserve_admin_session()"
    )
    op.create_table(
        "worker_status",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True)),
        sa.Column("last_successful_purge", sa.DateTime(timezone=True)),
        sa.Column("overdue_count", sa.Integer(), nullable=False),
        sa.Column("safe_failure_code", sa.Text()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_worker_status")),
        sa.CheckConstraint("id=1", name=op.f("ck_worker_status_singleton")),
        sa.CheckConstraint("overdue_count>=0", name=op.f("ck_worker_status_overdue_count_valid")),
        sa.CheckConstraint(
            "safe_failure_code IS NULL OR safe_failure_code IN "
            "('worker_not_started','database_unavailable','cleanup_failed','lock_timeout')",
            name=op.f("ck_worker_status_failure_code_safe"),
        ),
        schema="private",
    )
    op.execute(
        "REVOKE ALL ON FUNCTION private.secure_admin_hash(text), private.preserve_admin_session() "
        "FROM PUBLIC, slotbook_runtime, slotbook_backup"
    )
    op.execute("GRANT EXECUTE ON FUNCTION private.secure_admin_hash(text) TO slotbook_runtime")
    op.execute(
        "REVOKE ALL ON private.admins, private.admin_sessions, private.worker_status "
        "FROM PUBLIC, slotbook_runtime, slotbook_backup"
    )
    op.execute(
        "GRANT SELECT, INSERT ON private.admins, private.admin_sessions, private.worker_status "
        "TO slotbook_runtime"
    )
    op.execute("GRANT DELETE ON private.admin_sessions TO slotbook_runtime")
    op.execute(
        "GRANT UPDATE (last_heartbeat,last_successful_purge,overdue_count,safe_failure_code) "
        "ON private.worker_status TO slotbook_runtime"
    )


def downgrade() -> None:
    raise CommandError("database_downgrade_requires_reviewed_operator_procedure")
