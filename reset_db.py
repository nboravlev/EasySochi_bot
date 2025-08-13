from sqlalchemy.ext.asyncio import create_async_engine
import os
import asyncio
from sqlalchemy import text


DATABASE_URL = os.getenv("DATABASE_URL_ASYNC")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env")

# Пример: postgresql+asyncpg://user:pass@localhost/dbname
engine = create_async_engine(DATABASE_URL, echo=True)

async def reset_database():
    async with engine.begin() as conn:
        # Удаляем схемы (если есть)
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS apartments CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS events CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS media CASCADE"))

        await conn.execute(text("DROP EXTENSION IF EXISTS cron"))
        await conn.execute(text("DROP EXTENSION IF EXISTS postgis"))
        await conn.execute(text("DROP EXTENSION IF EXISTS pg_stat_statements"))
        await conn.execute(text("DROP EXTENSION IF EXISTS adminpack"))

        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE SCHEMA apartments"))
        await conn.execute(text("CREATE SCHEMA events"))
        await conn.execute(text("CREATE SCHEMA media"))

        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_cron"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS adminpack WITH SCHEMA pg_catalog"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))


    print("База данных очищена и сброшена до начального состояния.")

# Запуск
if __name__ == "__main__":
    asyncio.run(reset_database())
