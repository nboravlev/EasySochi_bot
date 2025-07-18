import os
from logging.config import fileConfig
from pathlib import Path
import geoalchemy2

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

#from db.models import * 
from db.db import Base
#from db.models import all

from db.models.users import User
from db.models.roles import Role
from db.models.sessions import Session

# Загрузка .env
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env")

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Логгинг
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метадата
# Metadata
print("Detected tables:", list(Base.metadata.tables.keys()))
target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
