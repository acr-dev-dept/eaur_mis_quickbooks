import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from dotenv import load_dotenv

from alembic import context

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models for autogenerate support
try:
    # Import Flask app to get the database metadata
    from application import create_app
    from application.models.central_models import BaseModel

    # Create app to get database context
    app = create_app('development')
    with app.app_context():
        from application import db
        target_metadata = db.metadata
except ImportError as e:
    print(f"Warning: Could not import models: {e}")
    # Fallback if models can't be imported
    target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url():
    """Get database URL from environment variables"""
    # Try to get from environment variables first
    database_url = os.getenv('DEV_DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')

    if not database_url:
        # Fallback to config file
        database_url = config.get_main_option("sqlalchemy.url")

    return database_url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get configuration section
    configuration = config.get_section(config.config_ini_section, {})

    # Override database URL from environment
    database_url = get_database_url()
    if database_url:
        configuration['sqlalchemy.url'] = database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,  # For SQLite compatibility
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
