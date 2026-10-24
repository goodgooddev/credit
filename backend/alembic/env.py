from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app import models  # noqa: F401  (импорт нужен, чтобы все таблицы попали в Base.metadata)
from app.config import get_settings
from app.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Таблицы, по которым Alembic строит автогенерацию миграций
target_metadata = Base.metadata


def _url() -> str:
    url = get_settings().sqlalchemy_url
    return url if isinstance(url, str) else url.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Подключение берём из тех же настроек, что и приложение (DB_HOST, DB_USER...)
    connectable = create_engine(get_settings().sqlalchemy_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
