import os
from sqlalchemy import text
import asyncio
from db.db_async import get_async_session
import logging


logger = logging.getLogger(__name__)

# Конфигурация

CHAT_ID = -1002843679066  # канал или чат

async def check_db(context):
    bot = context.bot
    job_data = context.job.data or {}
    last_status_ok = job_data.get("last_status_ok", None)

    try:
        async with get_async_session() as session:
            await session.execute(text("SELECT 1"))
        status_ok = True
        logger.info("✅ DB check passed")
    except Exception as e:
        status_ok = False
        logger.error(f"❌ DB check failed: {e}")

    if status_ok != last_status_ok:
        text_msg = (
            "✅ <b>База данных доступна</b>"
            if status_ok
            else "❌ <b>База данных недоступна!</b>"
        )
        await bot.send_message(chat_id=CHAT_ID, text=text_msg, parse_mode="HTML")

    # сохраняем состояние в job.data
    context.job.data = {"last_status_ok": status_ok}
