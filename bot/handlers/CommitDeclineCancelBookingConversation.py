from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton
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

from utils.escape import safe_html

from sqlalchemy import select, update as sa_update

from sqlalchemy.orm import selectinload

DECLINE_REASON = range(1)

async def booking_decline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Разбор данных из callback
    data_parts = query.data.split("_")
    status_id = int(data_parts[-2])  # статус (например, 8)
    booking_id = int(data_parts[-1])  # ID брони

    context.user_data["decline_booking_id"] = booking_id
    context.user_data["status_id"] = status_id

    # Запрашиваем причину
    keyboard = [[KeyboardButton("отправка причины")]]
    await query.message.reply_text(
        "❌ Укажите причину отклонения бронирования (макс. 255 символов):",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )

    return DECLINE_REASON


async def booking_decline_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text.strip()
    if not reason or reason.lower() == "отправка причины":
        reason = "Причина не указана"
    else:
        reason = safe_html(reason)[:255]

    booking_id = context.user_data.get("decline_booking_id")
    status_id = context.user_data.get("status_id")

    async with get_async_session() as session:
        # Обновляем статус и причину
        await session.execute(
            sa_update(Booking)
            .where(Booking.id == booking_id)
            .values(status_id=status_id, decline_reason=reason)
        )

        # Загружаем бронь с зависимостями
        result = await session.execute(
            select(Booking)
            .options(
                selectinload(Booking.apartment).selectinload(Apartment.apartment_type),
                selectinload(Booking.apartment).selectinload(Apartment.owner),
                selectinload(Booking.booking_type),
                selectinload(Booking.user)  # гость
            )
            .where(Booking.id == booking_id)
        )
        booking = result.scalar_one()

        await session.commit()

    # Определяем инициатора
    initiator_tg_id = update.effective_user.id
    guest_tg_id = booking.user.tg_user_id
    owner_tg_id = booking.apartment.owner.tg_user_id

    if initiator_tg_id == guest_tg_id:
        # Отмену делает гость → уведомляем владельца
        await context.bot.send_message(
            chat_id=owner_tg_id,
            text=(
                f"❌ Гость отменил бронирование. №{booking.id} ({booking.booking_type.name}).\n"
                f"Адрес: {booking.apartment.short_address}\n"
                f"C: {booking.check_in} по: {booking.check_out}\n"
                f"Причина: {reason}"
            )
        )
        confirm_text = "✅ Вы отменили бронирование, владелец уведомлён."
    else:
        # Отмену делает владелец → уведомляем гостя
        await context.bot.send_message(
            chat_id=guest_tg_id,
            text=(
                f"❌ Ваше бронирование №{booking.id} ({booking.booking_type.name}).\n"
                f"Адрес: {booking.apartment.short_address}\n"
                f"C: {booking.check_in} по: {booking.check_out}\n"
                f"Причина: {reason}\n\n"
                f"Хотите создать новое бронирование? 👉 /start"
            )
        )
        confirm_text = "✅ Бронирование отклонено, гость уведомлён."

    await update.message.reply_text(confirm_text, reply_markup=ReplyKeyboardRemove())

    # Чистим временные данные
    context.user_data.pop("decline_booking_id", None)
    context.user_data.pop("status_id", None)

    return ConversationHandler.END


# ✅ Only one function: booking confirmation
async def booking_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle booking confirmation by owner"""
    query = update.callback_query
    await query.answer()

    try:
        booking_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        await query.message.reply_text("❌ Ошибка: неверный ID бронирования")
        return ConversationHandler.END

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
            return ConversationHandler.END

        # ✅ Change status to Confirmed (id=6)
        booking.status_id = 6
        booking.updated_at = datetime.utcnow()
        await session.commit()

    # ✅ Send notification to guest with chat button
    keyboard = [
        [InlineKeyboardButton("💬 Перейти в чат", callback_data=f"chat_booking_enter_{booking_id}")]
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

    # ✅ Notify owner
    await context.bot.send_message(
        chat_id=booking.apartment.owner.tg_user_id,
        text=(
            f"✅ Вы подтвердили бронирование №{booking.id}.\n"
            f"Пользователь {booking.user.firstname or booking.user.tg_user_id} получил уведомление.\n"
            f"Проинструктируйте гостя о способах оплаты, алгоритме заселения и правилах проживания."
        )
    )

    # ✅ Update the original message (remove confirmation buttons)
    await query.edit_message_text(
        f"✅ Бронирование №{booking.id} подтверждено!\n"
        f"Чат с гостем активирован."
    )

    return ConversationHandler.END