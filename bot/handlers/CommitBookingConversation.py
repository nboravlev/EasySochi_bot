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

from bot.utils.escape import safe_html

from sqlalchemy import select, update as sa_update

from sqlalchemy.orm import selectinload

# Состояния
(
    GO_TO_CHAT,
    BOOKING_CHAT
) = range(2)


# ✅ 1. Обработчик кнопки Подтвердить
async def booking_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    booking_id = int(query.data.split(":")[-1])

    async with get_async_session() as session:
        result = await session.execute(
            select(Booking)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.apartment).selectinload(Apartment.owner)
            )
            .where(Booking.id == booking_id)
        )
        booking = result.scalar_one_or_none()
        if not booking:
            await query.message.reply_text("❌ Бронирование не найдено.")
            return
        
        # ✅ сохраняем нужные ID в контекст
        context.user_data["booking_id"] = booking.id
        context.user_data["renter_id"] = booking.user.id
        context.user_data["owner_id"] = booking.apartment.owner.id
        context.user_data["renter_tg_id"] = booking.user.tg_user_id
        context.user_data["owner_tg_id"] = booking.apartment.owner.tg_user_id

        # ✅ Меняем статус на Подтверждено (id=6)
        booking.status_id = 6
        await session.commit()

    # ✅ Отправляем пользователю уведомление с кнопкой Перейти в чат
    keyboard = [
        [InlineKeyboardButton("💬 Перейти в чат", callback_data=f"chat_booking_{booking_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=booking.user.tg_user_id,
        text=(
            f"✅ Ваше бронирование №{booking.id} подтверждено!\n\n"
            f"Для получения дополнительной информации и по вопросам оплаты "
            f"используйте встроенный чат ниже."
        ),
        reply_markup=reply_markup
    )

    # ✅ Уведомляем владельца
    await context.bot.send_message(
        chat_id=booking.apartment.owner.tg_user_id,
        text=(
            f"✅ Вы подтвердили бронирование №{booking.id}.\n"
            f"Пользователю {booking.user.tg_user_id} отправлено уведомление,\n"
            f"он свяжется с вами в ближайшее время.\n"
            f"Проинструктируйте гостя о способах оплаты, алгоритме заселения и правилах проживания"
        )
    )

    await query.message.reply_text("✅ Бронирование подтверждено, чат создан.")
    return GO_TO_CHAT

# ✅ 2. Обработчик кнопки Перейти в чат
async def open_booking_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    booking_id = int(query.data.split("_")[-1])
    context.user_data["chat_booking_id"] = booking_id

    await query.message.reply_text(
        f"💬 Вы вошли в чат бронирования №{booking_id}.\n"
        f"Отправьте первое сообщение."
    )
    return BOOKING_CHAT


# ✅ 3. Обработка сообщений в чате
async def handle_booking_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking_id = context.user_data.get("chat_booking_id")
    if not booking_id:
        return  # не в чате бронирования

    user_tg_id = update.effective_user.id
    renter_id = context.user_data.get("renter_id")
    owner_id = context.user_data.get("owner_id")
    renter_tg_id = context.user_data.get("renter_tg_id")
    owner_tg_id = context.user_data.get("owner_tg_id")
    text = update.message.text

    async with get_async_session() as session:
        
        sender_id = renter_id if user_tg_id == renter_tg_id else owner_id
        print(f"DEBUG sender_id: {sender_id}")
        # 💾 Сохраняем сообщение в БД
        chat_msg = BookingChat(
            booking_id=booking_id,
            sender_id=sender_id,
            message_text=text[:255],
            created_at=datetime.utcnow()
        )
        session.add(chat_msg)
        await session.commit()

    # 📤 Пересылаем сообщение другой стороне
    recipient_tg_id = owner_tg_id if sender_id == renter_id else renter_tg_id
    

    await context.bot.send_message(
        chat_id=recipient_tg_id,
        text=f"💬 Сообщение по бронированию №{booking_id}:\n{text}"
    )
