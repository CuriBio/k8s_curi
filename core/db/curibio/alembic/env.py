import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

section = config.config_ini_section
config.set_section_option(section, "POSTGRES_USER", os.environ.get("POSTGRES_USER"))
config.set_section_option(section, "POSTGRES_PASSWORD", os.environ.get("POSTGRES_PASSWORD"))
config.set_section_option(section, "POSTGRES_SERVER", os.environ.get("POSTGRES_SERVER"))
config.set_section_option(section, "POSTGRES_NAME", os.environ.get("POSTGRES_NAME"))
config.set_section_option(section, "TABLE_USER_PASS", os.environ.get("TABLE_USER_PASS"))
config.set_section_option(section, "TABLE_USER_PASS_RO", os.environ.get("TABLE_USER_PASS_RO"))
config.set_section_option(section, "MANTARRAY_RO_PASS", os.environ.get("MANTARRAY_RO_PASS"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction() as transaction:
        context.run_migrations()
        if "dry-run" in context.get_x_argument():
            print("Dry run complete, rolling back")
            transaction.rollback()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction() as transaction:
            context.run_migrations()
            if "dry-run" in context.get_x_argument():
                print("Dry run complete, rolling back")
                transaction.rollback()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
