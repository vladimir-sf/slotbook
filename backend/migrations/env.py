"""Explicit online migrations; no dotenv, application startup hook or SQL logging."""

import os

from alembic import context
from alembic.util import CommandError
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import DatabaseConfigurationError, create_database_engine, verify_database
from app.models import Base


def run_migrations() -> None:
    if context.is_offline_mode():
        raise CommandError("database_online_verification_required")
    engine = None
    try:
        # Deliberately no fallback to ordinary API/worker credentials.
        engine = create_database_engine(os.environ.get("MIGRATION_DATABASE_URL", ""))
        with engine.connect() as connection, connection.begin():
            verify_database(connection)
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                include_schemas=True,
                version_table_schema="public",
                transactional_ddl=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    except DatabaseConfigurationError as error:
        raise CommandError(str(error)) from None
    except SQLAlchemyError:
        raise CommandError("database_migration_failed") from None
    finally:
        if engine is not None:
            engine.dispose()


run_migrations()
