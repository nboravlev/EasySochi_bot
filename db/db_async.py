
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv(override=True)

# Получаем строку подключения из .env
DATABASE_URL = os.getenv("DATABASE_URL_ASYNC")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL_ASYNC is not set in .env")


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

async def get_async_session() -> AsyncSession:
    """
    Контекст‑менеджер для получения AsyncSession.
    Используйте в виде:
        async with get_async_session() as session:
            ...
    """
    async with async_session_maker() as session:
        yield session

# Базовый класс для моделей
Base = declarative_base()
