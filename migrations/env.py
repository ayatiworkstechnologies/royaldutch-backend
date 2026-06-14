from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, make_url, pool

from app.core.config import get_settings
from app.db.base import Base
from app import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    return str(get_settings().sqlalchemy_database_url)


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url()
    settings = get_settings()
    connect_args = {}
    url = make_url(configuration["sqlalchemy.url"])
    if settings.database_ssl and url.drivername.startswith("mysql"):
        connect_args["ssl"] = {}
        if settings.database_ssl_ca_path:
            connect_args["ssl_ca"] = settings.database_ssl_ca_path
        connect_args["ssl_verify_identity"] = settings.database_ssl_verify_identity
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
