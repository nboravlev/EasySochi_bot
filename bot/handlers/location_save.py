from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from sqlalchemy import select
from geoalchemy2.shape import from_shape

from shapely.geometry import Point

from bot.handlers.after_registration import proceed_after_registration
from db.db_async import get_async_session
from db.models.users import User
from db.models.sessions import Session

async def save_location(update: Update, context: ContextTypes.DEFAULT_TYPE):


    tg_user_id = update.effective_user.id
    role_id = context.user_data.get("role_id")
    session_id = context.user_data.get("session_id")
    is_new_user = context.user_data.get("is_new_user")


    async with get_async_session() as session:
        # 1. Находим пользователя по Telegram ID
        result = await session.execute(
            select(User).where(
            (User.tg_user_id == tg_user_id) &
            (User.role_id == role_id)
        )
        )
        user = result.scalar_one_or_none()

        if not user:
            await update.message.reply_text("Пользователь не найден.")
            return

        # 2. Ищем активную сессию
        result = await session.execute(
            select(Session)
            .where(Session.id == session_id, Session.is_active == True)           
            
        )
        active_session = result.scalar_one_or_none()

        if not active_session:
            await update.message.reply_text("Активная сессия не найдена.")
            return

        # 3. Обновляем геолокацию в формате POINT
       

        if update.message.text == "Не отправлять":
            user.location_lat = None
            user.location_lon = None
            await session.commit()
            await update.message.reply_text("Хорошо")
            if is_new_user:
                await update.message.reply_text("Регистрация пройдена успешно!")
            else:
                await update.message.reply_text("С возвращением!")
            await proceed_after_registration(update, context)
            return

        if update.message.location:
            user.location_lat = update.message.location.latitude
            user.location_lon = update.message.location.longitude
            lat = user.location_lat
            lon = user.location_lon
            point = from_shape(Point(lon, lat), srid=4326)
            active_session.location = point
            await session.commit()
            await update.message.reply_text("Спасибо! Геолокация получена.")
            
            if is_new_user:
                await update.message.reply_text("Регистрация пройдена успешно!")
            else:
                await update.message.reply_text("С возвращением!")
            await proceed_after_registration(update, context)
            return

        

# Экспорт хендлера
location_save_handler = MessageHandler(filters.LOCATION, save_location)

location_decline_handler = MessageHandler(filters.TEXT & filters.Regex("^Не отправлять$"), save_location)

