from db.db_async import get_async_session
from db.models.apartments import Apartment

from telegram.ext import ContextTypes,CallbackQueryHandler, ConversationHandler
from sqlalchemy import select, delete, update as sa_update
from telegram import Update

from datetime import datetime

from utils.logging_config import structured_logger



async def redo_apartment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    apartment_id = int(update.callback_query.data.split("_")[-1])
    try:
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
            structured_logger.info(
                "Reject new object",
                action="Reject new object",
                context={
                    'object_id':apartment_id
                }
            )

        await update.callback_query.edit_message_text("🚫 Данные удалены. Начните сначала /add_object")
    
    except Exception as e:

        structured_logger.error(
            f"Critical error in redo new object: {str(e)}",
            action="Redo new object",
            exception=e,
            context={
                'object_id': apartment_id,
                'error_type': type(e).__name__
            }
        )
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте позже или обратитесь в поддержку."
        )
    return ConversationHandler.END    


redo_apartment_handler = CallbackQueryHandler(
    redo_apartment_callback,
    pattern=r"^redo_apartment_\d+$"
)