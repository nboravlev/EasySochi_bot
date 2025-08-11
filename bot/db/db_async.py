
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os

from contextlib import asynccontextmanager
from typing import AsyncGenerator

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

if not (POSTGRES_USER and POSTGRES_PASSWORD and POSTGRES_DB):
    raise RuntimeError("Postgres credentials are not set in environment variables")

# Получаем строку подключения из .env
DATABASE_URL = DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@db:{POSTGRES_PORT}/{POSTGRES_DB}"



# Двигаем SQLAlchemy в async‑режим
engine = create_async_engine(
    DATABASE_URL,
    echo=True                # включить SQL‑логгинг
)


# factory для сессий
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # объекты не станут «откреплёнными» сразу после commit
)

#async def get_async_session() -> AsyncSession:
#    """
 #   Контекст‑менеджер для получения AsyncSession.
 #   Используйте в виде:
 #       async with get_async_session() as session:
  #          ...
  #  """
 #   async with async_session_maker() as session:
 #     yield session


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
       yield session

# Базовый класс для моделей
Base = declarative_base()
