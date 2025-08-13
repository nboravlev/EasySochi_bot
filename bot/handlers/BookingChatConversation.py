from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from datetime import datetime

from db.db_async import get_async_session

from db.models.bookings import Booking
from db.models.apartments import Apartment
from db.models.booking_chat import BookingChat
from db.models.users import User

from utils.escape import safe_html
from utils.anti_contact_filter import sanitize_message
from utils.booking_chat_message_history import send_booking_chat_history

from sqlalchemy import select, update as sa_update

from sqlalchemy.orm import selectinload


# Состояния
(
    GO_TO_CHAT,
    BOOKING_CHAT
) = range(2)



# ✅ 2. Обработчик кнопки Перейти в чат
async def open_booking_chat_from_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    
    try:
        booking_id = int(query.data.split("_")[-1])
        context.user_data["chat_booking_id"] = booking_id
    except (ValueError, IndexError):
        await query.message.reply_text("Ошибка: не найден ID бронирования")
        return ConversationHandler.END

    # Редактируем сообщение с кнопкой (убираем кнопку)
    await query.edit_message_reply_markup(reply_markup=None)

    await send_booking_chat_history(booking_id, update)
    
    # Отправляем приглашение в чат
    await query.message.reply_text(
        f"💬 Вы вошли в чат бронирования №{booking_id}.\n"
        "Отправьте свое сообщение.\n\n"
        "Для выхода используйте /exit_chat"
    )
    
    return BOOKING_CHAT

# ✅ 3. Обработка сообщений в чате
async def booking_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking_id = context.user_data.get("chat_booking_id")
    if not booking_id:
        return  # пользователь не в контексте чата бронирования

    text = update.message.text
    clean_text = sanitize_message(text)
    user_tg_id = update.effective_user.id

    async with get_async_session() as session:
        # 1. Получаем объект бронирования
        result = await session.execute(
            select(Booking).where(Booking.id == booking_id)
        )
        booking = result.scalar_one_or_none()
        if not booking:
            await update.message.reply_text("❌ Бронирование не найдено.")
            return

        # 2. Получаем информацию о гостях и владельце
        result = await session.execute(
            select(User).where(User.id == booking.user_id)
        )
        renter = result.scalar_one_or_none()
        if not renter:
            await update.message.reply_text("❌ Арендатор не найден.")
            return ConversationHandler.END

        result = await session.execute(
            select(Apartment).where(Apartment.id == booking.apartment_id)
        )
        apartment = result.scalar_one_or_none()
        if not apartment:
            await update.message.reply_text("❌ Объект не найден.")
            return ConversationHandler.END

        result = await session.execute(
            select(User).where(User.id == apartment.owner_id)
        )
        owner = result.scalar_one_or_none()
        if not owner:
            await update.message.reply_text("❌ Владелец не найден.")
            return ConversationHandler.END

        # 3. Определяем роль отправителя
        if user_tg_id == renter.tg_user_id:
            sender_id = renter.id
            recipient_tg_id = owner.tg_user_id
            sender_type = "guest"
        elif user_tg_id == owner.tg_user_id:
            sender_id = owner.id
            recipient_tg_id = renter.tg_user_id
            sender_type = "owner"
        else:
            await update.message.reply_text("❌ Вы не участник этого бронирования")
            return BOOKING_CHAT

        # 4. Сохраняем сообщение
        chat_msg = BookingChat(
            booking_id=booking_id,
            sender_id=sender_id,
            message_text=text[:255],
            created_at=datetime.utcnow()
        )
        session.add(chat_msg)
        await session.commit()

    # 5. Отправляем сообщение с КНОПКОЙ ДЛЯ ОТВЕТА
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Ответить", callback_data=f"chat_booking_enter_{booking_id}")]
    ])

    await context.bot.send_message(
        chat_id=recipient_tg_id,
        text=f"💬 Новое сообщение по бронированию №{booking_id}:\n\n{clean_text}\n\n"
             f"ℹ️ Отправитель: {'Гость' if sender_type == 'guest' else 'Собственник'}",
        reply_markup=reply_markup
    )

    return BOOKING_CHAT

async def enter_booking_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Извлекаем ID бронирования из callback_data
    booking_id = int(query.data.split("_")[-1])
    
    # Сохраняем в user_data
    context.user_data["chat_booking_id"] = booking_id
    
    # Отправляем подтверждение
    await query.edit_message_text(
        f"💬 Вы вошли в чат бронирования №{booking_id}\n"
        "Отправьте ваше сообщение..."
    )
    
    return BOOKING_CHAT

async def exit_booking_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "chat_booking_id" in context.user_data:
        del context.user_data["chat_booking_id"]
    
    await update.message.reply_text("Вы вышли из чата бронирования")
    return ConversationHandler.END