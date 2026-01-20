from datetime import timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from db.db_async import get_async_session
from db.models.bookings import Booking
from db.models.apartments import Apartment
from db.models.users import User

# Константы
TARGET_BOOKING_STATUS = 6      # "подтверждено"
BOOKING_STATUS_TIMEOUT = 12    # "завершено"


async def check_complit_booking(context):
    """Проверка и обработка завершенных броней"""

    bot = context.bot

    try:
        async with get_async_session() as session:
            stmt = (
                select(Booking)
                .options(
                    selectinload(Booking.apartment)
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


            for booking in complit_bookings:
                booking.status_id = BOOKING_STATUS_TIMEOUT
                await session.commit()
                await notify_complit_booking(bot, booking)

    except Exception as e:
        pass


async def notify_complit_booking(bot, booking):
    """Отправка уведомлений о том, что бронирование завершно"""

    guest_chat_id = booking.tg_user_id
    owner_chat_id = booking.apartment.owner_tg_id
    

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

