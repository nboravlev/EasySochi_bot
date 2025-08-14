import logging
from datetime import timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from db.db_async import get_async_session
from db.models.bookings import Booking
from db.models.apartments import Apartment
from db.models.users import User

logger = logging.getLogger(__name__)

# Константы
TARGET_BOOKING_STATUS = 5      # "ожидает подтверждения"
BOOKING_STATUS_TIMEOUT = 11    # "время истекло"



async def check_expired_booking(context):
    """Проверка и обработка просроченных броней"""
    bot = context.bot

    try:
        async with get_async_session() as session:
            stmt = (
                select(Booking)
                .options(
                    selectinload(Booking.apartment)
                    .selectinload(Apartment.owner),
                    selectinload(Booking.user)
                )
                .where(
                    Booking.status_id == TARGET_BOOKING_STATUS,
                    func.now() - Booking.created_at > timedelta(hours=24),
                    Booking.is_active == True
                )
            )

            result = await session.execute(stmt)
            expired_bookings = result.scalars().all()

            for booking in expired_bookings:
                booking.status_id = BOOKING_STATUS_TIMEOUT
                await session.commit()
                await notify_timeout(bot, booking)

    except Exception as e:
        logger.exception(f"Ошибка при обработке просроченных броней: {e}")


async def notify_timeout(bot, booking):
    """Отправка уведомлений о том, что бронь истекла"""
    guest_chat_id = booking.user.tg_user_id
    owner_chat_id = booking.apartment.owner.tg_user_id
    created_local = (booking.created_at + timedelta(hours=3)).replace(second=0, microsecond=0)

# Форматируем для сообщения
    created_str = created_local.strftime("%Y-%m-%d %H:%M")

    guest_text = (
        f"⏰ Ваш запрос на бронирование объекта <b>{booking.apartment.short_address}</b>\n"
        f"С: {booking.check_in} по: {booking.check_out}\n"
        f"отменен, так как истек срок ожидания подтверждения.\n"
        f"Хотите создать новое бронирование? /start"
    )

    owner_text = (
        f"⏰ Запрос на бронирование объекта <b>{booking.apartment.short_address}</b>,\n"
        f"Созданный и направленный вам для подтверждения: {created_str},\n"
        f"Стоимостью {booking.total_price} р.<b>‼️отменен‼️</b>\n"
        f"⌛️ Истек срок 24 часа на подтверждение"
    )

    await bot.send_message(chat_id=guest_chat_id, text=guest_text, parse_mode="HTML")
    await bot.send_message(chat_id=owner_chat_id, text=owner_text, parse_mode="HTML")
