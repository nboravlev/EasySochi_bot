import os
from logging.config import fileConfig
from pathlib import Path


from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

from db.models.users import User
from db.models.roles import Role
from db.models.sessions import Session
from db.models.apartments import Apartment
from db.models.apartment_types import ApartmentType

from db.models.bookings import Booking
from db.models.booking_types import BookingType

from db.models.images import Image

from db.db import Base

# Загрузка .env
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env")

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name == "spatial_ref_sys":
        return False
    if hasattr(object, 'schema') and object.schema == 'cron':
        return False
    return True

config = context.config
config.set_main_option(
    "sqlalchemy.url",
     DATABASE_URL
     )

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
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
            compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
