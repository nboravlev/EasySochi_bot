import os
from sqlalchemy import text
import asyncio
from db.db_async import get_async_session
from utils.logging_config import log_function_call, LogExecutionTime, get_logger


logger = get_logger(__name__)

# Конфигурация

CHAT_ID = -1002843679066  # канал или чат
@log_function_call(action="DB_monitor")
async def check_db(context):
    bot = context.bot

    try:
        async with get_async_session() as session:
            await session.execute(text("SELECT 1"))
        status_ok = True
        logger.info("🫥 DB_prod_rent check passed")
    except Exception as e:
        status_ok = False
        logger.error(f"❌ DB_prod_rent check failed: {e}")

    # ВСЕГДА отправляем статус, без проверки на изменение
    text_msg = (
        "🏡 <b>База данных prod_rent доступна</b>"
        if status_ok
        else "❄️ <b>База данных prod_rent недоступна!</b>"
    )
    
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text_msg, parse_mode="HTML")
    except Exception as send_error:
        logger.critical(f"🚨 Не удалось отправить уведомление о статусе БД: {send_error}")
