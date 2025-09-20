from db.db_async import get_async_session
from db.models.apartments import Apartment

from telegram.ext import ContextTypes,CallbackQueryHandler

from sqlalchemy import select, delete, update as sa_update

from telegram import Update

from datetime import datetime


async def redo_apartment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    apartment_id = int(update.callback_query.data.split("_")[-1])
    async with get_async_session() as session:
        await session.execute(
            sa_update(Apartment)
            .where(Apartment.id == apartment_id)
            .values(
                is_draft=True,
                is_active=False,  # Если хотите скрывать из поиска
                deleted_by=update.effective_user.id,  # Кто удалил (если есть контекст)
                updated_at=datetime.utcnow()  # Принудительное обновление (необязательно, но безопасно)
            )
        )

    await update.callback_query.edit_message_text("🚫 Данные удалены. Начните сначала /add_object")
    
    #return ADDRESS_INPUT

redo_apartment_handler = CallbackQueryHandler(
    redo_apartment_callback,
    pattern=r"^redo_apartment_\d+$"
)