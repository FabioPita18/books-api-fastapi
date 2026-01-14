"""
Alembic Environment Configuration

This file controls how Alembic runs migrations.

Key responsibilities:
1. Load database URL from application settings (not alembic.ini)
2. Import all SQLAlchemy models for autogenerate
3. Configure migration context
4. Handle online vs offline migrations

MIGRATION WORKFLOW:
===================
1. Make changes to SQLAlchemy models
2. Run: alembic revision --autogenerate -m "description"
3. Review the generated migration in alembic/versions/
4. Run: alembic upgrade head

COMMANDS:
- alembic revision --autogenerate -m "message"  # Create migration
- alembic upgrade head                           # Apply all migrations
- alembic downgrade -1                           # Rollback one migration
- alembic history                                # Show migration history
- alembic current                                # Show current revision
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# =============================================================================
# IMPORT APPLICATION COMPONENTS
# =============================================================================
# Import settings to get database URL
from app.config import get_settings

# Import Base and all models
# IMPORTANT: Import models package to ensure all models are registered
# with Base.metadata before autogenerate runs
from app.database import Base
from app.models import Book, Author, Genre  # noqa: F401 - needed for autogenerate

# Get application settings
settings = get_settings()

# =============================================================================
# ALEMBIC CONFIGURATION
# =============================================================================
# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url from settings (not alembic.ini)
# This ensures we use environment variables, not hardcoded values
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# =============================================================================
# METADATA FOR AUTOGENERATE
# =============================================================================
# This is the MetaData object that contains all table definitions.
# Alembic uses this to compare against the database and generate migrations.
#
# By importing all models above, they're registered with Base.metadata.
target_metadata = Base.metadata

# =============================================================================
# MIGRATION FUNCTIONS
# =============================================================================


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Offline mode generates SQL scripts without connecting to the database.
    Useful for:
    - Generating SQL to review before running
    - Environments where you can't connect to the DB
    - CI/CD pipelines that need to create migration SQL files

    Usage:
        alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include object type in comparisons (for accurate autogenerate)
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Online mode connects to the database and applies migrations directly.
    This is the normal way to run migrations.

    Usage:
        alembic upgrade head
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't pool connections for migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Compare column types (not just names)
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# =============================================================================
# RUN MIGRATIONS
# =============================================================================
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
