"""T011 public configuration, stable schedule constraints and explicit ACLs.

Frozen DDL is intentionally independent of current application model imports.
No booking/private tables, data seed, automatic downgrade or future-table grants.
"""

import sqlalchemy as sa
from alembic import op
from alembic.util import CommandError
from sqlalchemy.dialects import postgresql

revision = "0002_configuration"
down_revision = "0001_schemas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activities")),
        sa.UniqueConstraint("slug", name=op.f("uq_activities_slug")),
        sa.CheckConstraint(
            "char_length(description) BETWEEN 1 AND 2000 AND description = btrim(description, "
            r"U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680"
            r"\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000')",
            name=op.f("ck_activities_description_valid"),
        ),
        sa.CheckConstraint(
            "duration_minutes > 0 AND duration_minutes % 15 = 0",
            name=op.f("ck_activities_duration_minutes_valid"),
        ),
        schema="public",
    )
    op.create_table(
        "weekly_windows",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("iso_weekday", sa.SmallInteger(), nullable=False),
        sa.Column("start_local_time", postgresql.TIME(timezone=False, precision=6), nullable=False),
        sa.Column("end_local_time", postgresql.TIME(timezone=False, precision=6), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_weekly_windows")),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["public.activities.id"],
            ondelete="RESTRICT",
            name=op.f("fk_weekly_windows_activity_id_activities"),
        ),
        sa.CheckConstraint(
            "iso_weekday BETWEEN 1 AND 7", name=op.f("ck_weekly_windows_iso_weekday_valid")
        ),
        sa.CheckConstraint(
            "end_local_time > start_local_time AND "
            "start_local_time < TIME '24:00:00' AND end_local_time < TIME '24:00:00'",
            name=op.f("ck_weekly_windows_local_window_valid"),
        ),
        postgresql.ExcludeConstraint(
            ("activity_id", "="),
            ("iso_weekday", "="),
            (
                sa.text(
                    "numrange(EXTRACT(EPOCH FROM start_local_time) * 1000000, "
                    "EXTRACT(EPOCH FROM end_local_time) * 1000000, '[)')"
                ),
                "&&",
            ),
            name="no_overlap_weekly_windows",
            using="gist",
        ),
        schema="public",
    )
    op.create_table(
        "blocked_dates",
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("activity_id", "local_date", name=op.f("pk_blocked_dates")),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["public.activities.id"],
            ondelete="RESTRICT",
            name=op.f("fk_blocked_dates_activity_id_activities"),
        ),
        schema="public",
    )
    # Revoke explicitly as well as relying on 0001's fail-closed defaults.
    op.execute(
        "REVOKE ALL ON public.activities, public.weekly_windows, public.blocked_dates "
        "FROM PUBLIC, slotbook_runtime, slotbook_backup"
    )
    op.execute(
        "GRANT SELECT, INSERT ON public.activities, public.weekly_windows, "
        "public.blocked_dates TO slotbook_runtime"
    )
    op.execute("GRANT UPDATE ON public.activities, public.weekly_windows TO slotbook_runtime")
    # Schedule replacement deletes windows; MVP has no activity delete/unblock.
    op.execute("GRANT DELETE ON public.weekly_windows TO slotbook_runtime")
    # Column grants keep future added columns out of backups until reviewed.
    op.execute(
        "GRANT SELECT (id, slug, title, description, duration_minutes, timezone, is_active) "
        "ON public.activities TO slotbook_backup"
    )
    op.execute(
        "GRANT SELECT (id, activity_id, iso_weekday, start_local_time, end_local_time) "
        "ON public.weekly_windows TO slotbook_backup"
    )
    op.execute("GRANT SELECT (activity_id, local_date) ON public.blocked_dates TO slotbook_backup")


def downgrade() -> None:
    raise CommandError("database_downgrade_requires_reviewed_operator_procedure")
