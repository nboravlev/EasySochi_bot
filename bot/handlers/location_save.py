from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from sqlalchemy import select
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from db.db_async import get_async_session
from db.models.users import User
from db.models.sessions import Session

async def save_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    if location is None:
        return

    tg_user_id = update.effective_user.id
    lat = location.latitude
    lon = location.longitude

    async for session in get_async_session():
        # 1. Находим пользователя по Telegram ID
        result = await session.execute(
            select(User).where(User.tg_user_id == tg_user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await update.message.reply_text("Пользователь не найден.")
            return

        # 2. Ищем активную сессию по user.id
        result = await session.execute(
            select(Session)
            .where(Session.user_id == user.id, Session.is_active == True)
            .order_by(Session.created_at.desc())
            .limit (1)  # если вдруг несколько активных
        )
        active_session = result.scalar_one_or_none()

        if not active_session:
            await update.message.reply_text("Активная сессия не найдена.")
            return

        # 3. Обновляем геолокацию в формате POINT
        point = from_shape(Point(lon, lat), srid=4326)
        active_session.location = point

        await session.commit()

        await update.message.reply_text("✅ Локация успешно сохранена!")

# Экспорт хендлера
location_save_handler = MessageHandler(filters.LOCATION, save_location)
