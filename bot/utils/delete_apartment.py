from sqlalchemy import select, exists, or_, and_, update as sa_update
from datetime import datetime
from sqlalchemy.orm import selectinload
from db.db_async import get_async_session
from db.models.apartments import Apartment
from db.models.search_sessions import SearchSession
from db.models.booking_types import BookingType
from db.models.bookings import Booking
from utils.logging_config import (
    structured_logger, 
    log_db_select, 
    log_db_insert, 
    log_db_update,
    log_db_delete,
    LoggingContext,
    monitor_performance
)

from telegram import Update

from telegram.ext import ContextTypes


# Предположим, статус 5 = "pending", статус 6 = "confirmed"
ACTIVE_BOOKING_STATUSES = [5, 6]


@log_db_update  
async def delete_apartment(apartment_id: int, tg_user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete apartment with full logging"""
    ACTIVE_BOOKING_STATUSES = [5, 6]
    
    with LoggingContext("apartment_deletion", user_id=tg_user_id, 
                       apartment_id=apartment_id) as log_ctx:
        
        structured_logger.warning(
            f"User attempting to delete apartment {apartment_id}",
            user_id=tg_user_id,
            action="apartment_deletion_attempt",
            context={'apartment_id': apartment_id}
        )
        
        async with get_async_session() as session:
            # Check apartment and bookings
            result = await session.execute(
                select(Apartment)
                .options(selectinload(Apartment.booking))
                .where(Apartment.id == apartment_id)
            )
            apartment = result.scalar_one_or_none()

            if not apartment:
                structured_logger.warning(
                    f"Apartment {apartment_id} not found for deletion",
                    user_id=tg_user_id,
                    action="apartment_not_found",
                    context={'apartment_id': apartment_id}
                )
                await update.callback_query.message.reply_text("❌ Объект не найден.")
                return 

            # Check for active bookings
            active_bookings = [b for b in apartment.booking if b.status_id in ACTIVE_BOOKING_STATUSES]
            
            if active_bookings:
                structured_logger.warning(
                    f"Cannot delete apartment {apartment_id} - has active bookings",
                    user_id=tg_user_id,
                    action="apartment_deletion_blocked",
                    context={
                        'apartment_id': apartment_id,
                        'active_bookings_count': len(active_bookings),
                        'booking_ids': [b.id for b in active_bookings]
                    }
                )
                await update.callback_query.message.reply_text(
                    "🚫 На данном объекте есть активные бронирования. "
                    "Сообщите администратору о вашей проблеме. /help"
                )
                return 

            # Perform soft deletion
            await session.execute(
                sa_update(Apartment)
                .where(Apartment.id == apartment_id)
                .values(
                    is_active=False,
                    updated_at=datetime.utcnow(),
                    deleted_by=tg_user_id
                )
            )
            await session.commit()

            structured_logger.info(
                f"Apartment {apartment_id} successfully deleted",
                user_id=tg_user_id,
                action="apartment_deleted",
                context={
                    'apartment_id': apartment_id,
                    'apartment_title': apartment.title[:50] if apartment.title else None,
                    'deletion_type': 'soft_delete'
                }
            )

            await update.callback_query.message.reply_text("✅ Объект успешно удалён.")
            return 