from db.db_async import get_async_session
from db.models.apartments import Apartment

from telegram.ext import ContextTypes,CallbackQueryHandler,ConversationHandler

from sqlalchemy import select

from telegram import Update

from utils.logging_config import structured_logger


async def confirm_apartment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        apartment_id = int(update.callback_query.data.split("_")[-1])
        async with get_async_session() as session:
            result = await session.execute(select(Apartment).where(Apartment.id == apartment_id))
            apt = result.scalar_one_or_none()
            if not apt:
                await update.callback_query.answer("Объект не найден.")
                return

            apt.is_draft = False
            await session.commit()
            structured_logger.info(
                "Complite new object",
                action="Complit new object",
                context={
                    'object_id':apartment_id
                }
            )

        await update.callback_query.edit_message_text("✅ Объект подтверждён и готов к показу арендаторам!")
    
    except Exception as e:

        structured_logger.error(
            f"Critical error in complit new object: {str(e)}",
            action="Complit new object",
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

confirm_apartment_handler = CallbackQueryHandler(
    confirm_apartment_callback,
    pattern=r"^confirm_apartment_\d+$"
)