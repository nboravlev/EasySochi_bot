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

from sqlalchemy import select

async def booking_chat_message(current_booking: int,update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking_id = current_booking
    if not booking_id:
        return  # пользователь не в контексте чата бронирования

    text = update.message.text
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

        # 2. Получаем арендатора (user_id -> tg_user_id)
        result = await session.execute(
            select(User).where(User.id == booking.user_id)
        )
        renter = result.scalar_one_or_none()
        if not renter:
            await update.message.reply_text("❌ Арендатор не найден.")
            return

        renter_id = renter.id
        renter_tg_id = renter.tg_user_id

        # 3. Получаем владельца по apartment.owner_id
        result = await session.execute(
            select(Apartment).where(Apartment.id == booking.apartment_id)
        )
        apartment = result.scalar_one_or_none()
        if not apartment:
            await update.message.reply_text("❌ Объект не найден.")
            return

        owner_id = apartment.owner_id

        result = await session.execute(
            select(User).where(User.id == owner_id)
        )
        owner = result.scalar_one_or_none()
        if not owner:
            await update.message.reply_text("❌ Владелец не найден.")
            return

        owner_tg_id = owner.tg_user_id

        # 4. Определяем отправителя
        sender_id = renter_id if user_tg_id == renter_tg_id else owner_id

        # 5. Сохраняем сообщение
        chat_msg = BookingChat(
            booking_id=booking_id,
            sender_id=sender_id,
            message_text=text[:255],
            created_at=datetime.utcnow()
        )
        session.add(chat_msg)
        await session.commit()

    # 6. Определяем получателя
    recipient_tg_id = owner_tg_id if sender_id == renter_id else renter_tg_id

    # 7. Пересылаем сообщение
    await context.bot.send_message(
        chat_id=recipient_tg_id,
        text=f"💬 Сообщение по бронированию №{booking_id}:\n{text}"
    )
