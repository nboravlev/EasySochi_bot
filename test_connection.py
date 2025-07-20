import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv, dotenv_values
import os

# Загружаем .env с перезаписью переменных
load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
print("DATABASE_URL from .env:", DATABASE_URL)
print(dotenv_values())

# Тест асинхронного подключения
async def test_connection():
    try:
        engine = create_async_engine(DATABASE_URL, echo=True)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Connection successful:", result.scalar())
    except Exception as e:
        print("❌ Connection failed:")
        print(e)

# Запуск
asyncio.run(test_connection())
