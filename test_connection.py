from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем строку подключения
DATABASE_URL = os.getenv("DATABASE_URL")
print("DATABASE_URL from .env:", DATABASE_URL)

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        print("✅ Connection successful!")
        print(f"PostgreSQL version: {result.fetchone()[0]}")
except Exception as e:
    print(f"❌ Connection failed:\n{e}")