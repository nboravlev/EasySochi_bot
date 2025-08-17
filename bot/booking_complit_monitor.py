from datetime import timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from db.db_async import get_async_session
from db.models.bookings import Booking
from db.models.apartments import Apartment
from db.models.users import User

from utils.logging_config import log_function_call, LogExecutionTime, get_logger


# Константы
TARGET_BOOKING_STATUS = 6      # "подтверждено"
BOOKING_STATUS_TIMEOUT = 12    # "завершено"


@log_function_call(action="check_complit_booking")
async def check_complit_booking(context):
    """Проверка и обработка завершенных броней"""
    logger = get_logger(__name__)
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
                    and_(
                    Booking.status_id == TARGET_BOOKING_STATUS,
                    func.now() > Booking.check_out,
                    Booking.is_active == True
                    )
                )
            )

            result = await session.execute(stmt)
            complit_bookings = result.scalars().all()

            logger.info(
                f"Found {len(complit_bookings)} complit bookings to process",
                extra={
                    "action": "check_complit_booking",
                    "booking_ids": [b.id for b in complit_bookings]
                }
            )

            for booking in complit_bookings:
                booking.status_id = BOOKING_STATUS_TIMEOUT
                await session.commit()
                await notify_complit_booking(bot, booking)

    except Exception as e:
        logger.exception(f"Ошибка при обработке завершенных броней: {e}")


async def notify_complit_booking(bot, booking):
    """Отправка уведомлений о том, что бронирование завершно"""
    logger = get_logger(__name__)
    guest_chat_id = booking.user.tg_user_id
    owner_chat_id = booking.apartment.owner.tg_user_id
    

    guest_text = (
        f"⏰ Бронирование № <b>{booking.id}</b>\n"
        f"Адрес: <b>{booking.apartment.short_address}</b>\n"
        f"С: {booking.check_in} по: {booking.check_out}\n"
        f"Завершено. Будем рады снова видеть вас в числе наших пользователей\n"
    )
#todo: продумать логику взаимодейсnвия, запрашивать отзывы и оценки
    owner_text = (
        f"⏰ Бронирование № <b>{booking.id}</b>\n"
        f"Адрес: <b>{booking.apartment.short_address}</b>\n"
        f"С: {booking.check_in} по: {booking.check_out}\n"
        f"Завершено. Надеемся, что все прошло хорошо\n"
    )
#todo: продумать логику взаимодейсnвия, запрашивать отзывы и оценки

    await bot.send_message(chat_id=guest_chat_id, text=guest_text, parse_mode="HTML")
    await bot.send_message(chat_id=owner_chat_id, text=owner_text, parse_mode="HTML")

    logger.info(
        f"Booking complit notifications sent for booking {booking.id}",
        extra={
            "action": "notify_timeout",
            "booking_id": booking.id,
            "guest_chat_id": guest_chat_id,
            "owner_chat_id": owner_chat_id
        }
    )