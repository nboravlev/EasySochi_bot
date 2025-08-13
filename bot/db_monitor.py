import os
from sqlalchemy import text
import asyncio
from db.db_async import get_async_session
import logging

# Конфигурация

CHAT_ID = -1002843679066  # канал или чат
CHECK_INTERVAL = 30 * 60  # 30 минут

logger = logging.getLogger(__name__)

async def check_db(bot):
    last_status_ok = None

    while True:
        try:
            async with get_async_session() as session:
                await session.execute(text("SELECT 1"))
            status_ok = True
            logger.info("✅ DB check passed")
        except Exception as e:
            status_ok = False
            logger.error(f"❌ DB check failed: {e}")

        if status_ok != last_status_ok:
            if status_ok:
                text_msg = "✅ <b>База данных доступна</b>"
            else:
                text_msg = "❌ <b>База данных недоступна!</b>"
            await bot.send_message(chat_id=CHAT_ID, text=text_msg, parse_mode="HTML")

        last_status_ok = status_ok
        await asyncio.sleep(CHECK_INTERVAL)