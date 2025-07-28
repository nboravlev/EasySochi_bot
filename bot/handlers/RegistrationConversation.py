from telegram import ReplyKeyboardMarkup, KeyboardButton, Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
)
from sqlalchemy import update as sa_update, select 
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from datetime import datetime
import logging

from db.db_async import get_async_session
from db.models.users import User
from db.models.sessions import Session
from db.models.roles import Role
from bot.utils.user_session import register_user_and_session

logger = logging.getLogger(__name__)

# === Состояния ===
CHOOSING_ROLE, ASK_PHONE, ASK_LOCATION = range(3)

# === Роли ===
ROLE_MAP = {
    "🏠 Хочу арендовать жильё": 1,  # tenant
    "🏘 Хочу сдавать жильё": 2     # owner
}

# === Старт ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [[role] for role in ROLE_MAP.keys()]
        await update.message.reply_text(
            "Привет! Что вы хотите сделать:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return CHOOSING_ROLE
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        return ConversationHandler.END

# === Выбор роли и регистрация ===
async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        role_text = update.message.text
        if role_text not in ROLE_MAP:
            await update.message.reply_text("Пожалуйста, выберите из предложенных вариантов.")
            return CHOOSING_ROLE

        role_id = ROLE_MAP[role_text]
        tg_user = update.effective_user
        bot_id = context.bot.id
        print(f"результат запроса в ТГ{tg_user}")
        logger.info(f"User {tg_user.id} chose role: {role_id}")
        
        # ✅ Регистрируем пользователя и создаём сессию
        user, session, is_new_user = await register_user_and_session(tg_user, bot_id, role_id)
        context.user_data.update({
            "user_id": user.id,
            "session_id": session.id,
            "role_id": role_id,
            "is_new_user": is_new_user,
            "tg_user_id": tg_user.id
        })

        if not user.phone_number:
            await update.message.reply_text(
                "Спасибо! Вы выбрали роль.",
                reply_markup=ReplyKeyboardRemove()
            )
            keyboard = [
                [KeyboardButton("📞 Отправить телефон", request_contact=True)], 
                ["Пропустить"]
            ]
            await update.message.reply_text(
                "Пожалуйста, отправьте ваш номер телефона (или нажмите 'Пропустить'):",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            )
            return ASK_PHONE
        else:
            await update.message.reply_text(
                "Ваш номер уже есть в базе.",
                reply_markup=ReplyKeyboardRemove()
            )
            return await _ask_for_location(update)
            
    except Exception as e:
        logger.error(f"Error in choose_role: {e}")
        await update.message.reply_text("Произошла ошибка при регистрации.")
        return ConversationHandler.END

# === Сохранение телефона ===
async def save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        phone = None
        
        if update.message.contact:  
            phone = update.message.contact.phone_number
        elif update.message.text == "Пропустить":
            phone = None
        else:
            await update.message.reply_text("Нажмите кнопку отправки телефона или 'Пропустить':")
            return ASK_PHONE

        # ✅ Исправлен баг с сессией
        if phone:
            async with get_async_session() as session:
                await session.execute(
                    sa_update(User)
                    .where(User.id == context.user_data["user_id"])
                    .values(phone_number=phone, updated_at=datetime.utcnow())
                )
                await session.commit()
            
            await update.message.reply_text(
                "Спасибо! Номер телефона сохранён.",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text(
                "Хорошо, пропускаем номер телефона.",
                reply_markup=ReplyKeyboardRemove()
            )

        # ✅ Запрашиваем геолокацию
        return await _ask_for_location(update)
        
    except Exception as e:
        logger.error(f"Error saving phone: {e}")
        await update.message.reply_text("Ошибка при сохранении номера.")
        return ConversationHandler.END

# === Сохранение геолокации ===
async def save_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        is_new_user = context.user_data["is_new_user"]
        session_id = context.user_data["session_id"]
        
        location_saved = False
        
        if update.message.location:
            lat = update.message.location.latitude
            lon = update.message.location.longitude
            point = from_shape(Point(lon, lat), srid=4326)
            
            # ✅ Исправлен баг с сессией
            async with get_async_session() as session:
                await session.execute(
                    sa_update(Session)
                    .where(Session.id == session_id)
                    .values(location=point, updated_at=datetime.utcnow())
                )
                await session.commit()
            
            await update.message.reply_text(
                "Спасибо! Геолокация сохранена.",
                reply_markup=ReplyKeyboardRemove()
            )
            location_saved = True
            
        elif update.message.text == "Не отправлять":
            await update.message.reply_text(
                "Хорошо, геолокация не сохранена.",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text("Выберите: отправить геолокацию или 'Не отправлять':")
            return ASK_LOCATION
        
        # Финальное сообщение
        if is_new_user:
            await update.message.reply_text("🎉 Регистрация завершена успешно!")
        else:
            await update.message.reply_text("👋 Рады видеть вас снова!")
        
        return await _handle_redirect(update, context)
        
    except Exception as e:
        logger.error(f"Error saving location: {e}")
        await update.message.reply_text("Ошибка при сохранении геолокации.")
        return ConversationHandler.END

async def redirect_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        role_id = context.user_data["role_id"]

        if role_id == 1:  # tenant
            await update.message.reply_text("🔍 Для поиска жилья нажмите /start_search")
        else:  # owner
            await update.message.reply_text("🏠 Для добавления объекта нажмите /add_object")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in redirect_next: {e}")
        await update.message.reply_text("Ошибка перенаправления.")
        return ConversationHandler.END

# === Вспомогательная функция ===
async def _ask_for_location(update):
    """Вспомогательная функция для запроса геолокации"""
    keyboard = [
        [KeyboardButton("📍 Отправить геолокацию", request_location=True)], 
        ["Не отправлять"]
    ]
    await update.message.reply_text(
        "Для улучшения поиска поделитесь геолокацией или нажмите 'Не отправлять':",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return ASK_LOCATION

async def _handle_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вспомогательная функция для обработки редиректа"""
    try:
        role_id = context.user_data["role_id"]

        if role_id == 1:  # tenant
            await update.message.reply_text("🔍 Для поиска жилья нажмите /start_search")
        else:  # owner
            await update.message.reply_text("🏠 Для добавления объекта нажмите /add_object")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in redirect: {e}")
        await update.message.reply_text("Ошибка перенаправления.")
        return ConversationHandler.END
# === Отмена ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Регистрация отменена.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END