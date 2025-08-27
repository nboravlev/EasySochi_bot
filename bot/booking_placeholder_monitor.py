from datetime import timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload, aliased
from db.db_async import get_async_session
from db.models.bookings import Booking
from db.models.apartments import Apartment
from db.models.users import User

from utils.logging_config import log_function_call, LogExecutionTime, get_logger


# Константы
TARGET_BOOKING_STATUS = [5,6,8,11]      
BOOKING_STATUS_TIMEOUT = 7    # заглушка


@log_function_call(action="check_placeholder_booking")
async def check_placeholder_booking(context):
    """Проверка и обработка завершенных броней"""
    logger = get_logger(__name__)
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
                        Booking.status_id.in_(TARGET_BOOKING_STATUS),
                        Booking.is_active == True,
                        Booking.tg_user_id == Apartment.tg_user_id  # проверка tg_user_id
                    )
                )
            )

            result = await session.execute(stmt)
            placehold_bookings = result.scalars().all()

            logger.info(
                f"Found {len(placehold_bookings)} placeholder bookings to process",
                extra={
                    "action": "check_placeholder_booking",
                    "booking_ids": [b.id for b in placehold_bookings]
                }
            )

            for booking in placehold_bookings:
                booking.status_id = BOOKING_STATUS_TIMEOUT
            await session.commit()

    except Exception as e:
        logger.exception(f"Ошибка при обработке завершенных броней: {e}")


