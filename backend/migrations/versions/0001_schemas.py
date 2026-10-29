"""T009: restricted schema/role foundation, no application entities or seed data.

The fixed migration principal owns objects. Runtime/backup are passwordless
NOLOGIN privilege groups; separate operator-provisioned logins may join them.
Existing elevated/group-member roles fail rather than silently changing cluster
security. No default access is granted: later revisions must allowlist each table
and the exact backup columns. Role/database ACLs apply only to this database;
the two group names are cluster-wide and must be reserved for SlotBook.
"""

from alembic import op
from alembic.util import CommandError

revision = "0001_schemas"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE role_name text;
        BEGIN
          FOREACH role_name IN ARRAY ARRAY['slotbook_runtime', 'slotbook_backup'] LOOP
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
              EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE '
                             'NOINHERIT NOREPLICATION NOBYPASSRLS', role_name);
            END IF;
            IF EXISTS (
              SELECT 1 FROM pg_roles r WHERE r.rolname = role_name AND
                (r.rolcanlogin OR r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR
                 r.rolinherit OR r.rolreplication OR r.rolbypassrls OR
                 EXISTS (SELECT 1 FROM pg_auth_members m WHERE m.member = r.oid))
            ) OR current_user = role_name THEN
              RAISE EXCEPTION 'database_role_configuration_invalid';
            END IF;
          END LOOP;
        END $$
        """
    )
    op.execute("CREATE SCHEMA IF NOT EXISTS public AUTHORIZATION CURRENT_USER")
    op.execute("CREATE SCHEMA IF NOT EXISTS private AUTHORIZATION CURRENT_USER")
    op.execute("ALTER SCHEMA public OWNER TO CURRENT_USER")
    op.execute("ALTER SCHEMA private OWNER TO CURRENT_USER")
    # PUBLIC normally has CONNECT/TEMP, and older templates may allow CREATE.
    op.execute(
        """
        DO $$ BEGIN
          EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC, slotbook_runtime, '
                         'slotbook_backup', current_database());
          EXECUTE format('GRANT CONNECT ON DATABASE %I TO slotbook_runtime, slotbook_backup',
                         current_database());
        END $$
        """
    )
    op.execute(
        "REVOKE ALL ON SCHEMA public, private FROM PUBLIC, slotbook_runtime, slotbook_backup"
    )
    op.execute("GRANT USAGE ON SCHEMA public TO slotbook_runtime, slotbook_backup")
    op.execute("GRANT USAGE ON SCHEMA private TO slotbook_runtime")
    # Remove both global and schema-specific defaults for this migration owner.
    # A schema REVOKE alone cannot cancel a global default GRANT.
    for scope in ("", "IN SCHEMA public, private "):
        for objects in ("TABLES", "SEQUENCES", "FUNCTIONS"):
            op.execute(
                f"ALTER DEFAULT PRIVILEGES {scope}REVOKE ALL ON {objects} "
                "FROM PUBLIC, slotbook_runtime, slotbook_backup"
            )
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public")
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace
                         WHERE e.extname = 'btree_gist' AND n.nspname = 'public') THEN
            RAISE EXCEPTION 'database_extension_configuration_invalid';
          END IF;
        END $$
        """
    )
    # Includes the Alembic version table; only the migration owner may read/write it.
    for objects in ("TABLES", "SEQUENCES", "FUNCTIONS"):
        op.execute(
            f"REVOKE ALL ON ALL {objects} IN SCHEMA public, private "
            "FROM PUBLIC, slotbook_runtime, slotbook_backup"
        )


def downgrade() -> None:
    # Never drop shared cluster roles, schema/data or extension during recovery.
    raise CommandError("database_downgrade_requires_reviewed_operator_procedure")
