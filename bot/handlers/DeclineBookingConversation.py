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

from db.db_async import get_async_session

from db.models.bookings import Booking

from bot.utils.escape import safe_html

from sqlalchemy import select, update as sa_update

from sqlalchemy.orm import selectinload

DECLINE_REASON = range(1)

async def booking_decline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Получаем booking_id из callback_data
    booking_id = int(query.data.split(":")[1])
    context.user_data["decline_booking_id"] = booking_id

    # ⚡ Обновляем статус бронирования на "Отклонено" (id=8)
    async with get_async_session() as session:
        await session.execute(
            sa_update(Booking)
            .where(Booking.id == booking_id)
            .values(status_id=8)
        )
        await session.commit()

    # Запрашиваем причину отклонения
    await query.message.reply_text("❌ Укажите причину отклонения бронирования (макс. 255 символов):")

    return DECLINE_REASON

async def booking_decline_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = safe_html(update.message.text.strip())

    # ⚠️ Ограничиваем длину до 255 символов
    if len(reason) > 255:
        reason = reason[:255]

    booking_id = context.user_data.get("decline_booking_id")

    # ✅ Сохраняем причину в БД
    async with get_async_session() as session:
        await session.execute(
            sa_update(Booking)
            .where(Booking.id == booking_id)
            .values(decline_reason=reason)
        )
        await session.commit()

        # Получаем booking для отправки уведомления пользователю
        result = await session.execute(
            select(Booking)
            .options(selectinload(Booking.user))
            .where(Booking.id == booking_id)
        )
        booking = result.scalar_one()

    # ✅ Отправляем уведомление пользователю
    await context.bot.send_message(
        chat_id=booking.user.tg_user_id,
        text=(
            f"❌ Ваше бронирование №{booking.id} не подтверждено.\n"
            f"Причина: {reason}\n\n"
            f"Хотите создать новое бронирование? 👉 /start_search"
        )
    )

    await update.message.reply_text("✅ Бронирование отклонено, пользователь уведомлен.")
    context.user_data.pop("decline_booking_id", None)

    return ConversationHandler.END
