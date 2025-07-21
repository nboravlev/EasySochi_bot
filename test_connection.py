import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, create_engine
from dotenv import load_dotenv, dotenv_values
import os

# Загружаем переменные из .env
load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL_ASYNC = os.getenv("DATABASE_URL_ASYNC")

print("DATABASE_URL =", DATABASE_URL)
print("DATABASE_URL_ASYNC =", DATABASE_URL_ASYNC)
print("Env loaded:", dotenv_values())

# Тест синхронного подключения (для Alembic)
def test_sync_connection():
    try:
        engine = create_engine(DATABASE_URL, echo=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Sync Connection successful:", result.scalar())
    except Exception as e:
        print("❌ Sync connection failed:")
        print(e)

# Тест асинхронного подключения (для бота)
async def test_async_connection():
    try:
        engine = create_async_engine(DATABASE_URL_ASYNC, echo=True)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Async Connection successful:", result.scalar())
    except Exception as e:
        print("❌ Async connection failed:")
        print(e)

# Запуск обоих тестов
if __name__ == "__main__":
    test_sync_connection()
    asyncio.run(test_async_connection())

