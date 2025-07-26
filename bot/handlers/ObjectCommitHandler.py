from db.db_async import get_async_session
from db.models.apartments import Apartment

from telegram.ext import ContextTypes,CallbackQueryHandler

from sqlalchemy import select

from telegram import Update

async def confirm_apartment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    apartment_id = int(update.callback_query.data.split("_")[-1])
    async with get_async_session() as session:
        result = await session.execute(select(Apartment).where(Apartment.id == apartment_id))
        apt = result.scalar_one_or_none()
        if not apt:
            await update.callback_query.answer("Объект не найден.")
            return

        apt.is_draft = False
        await session.commit()

    await update.callback_query.edit_message_text("✅ Объект подтверждён и готов к показу арендаторам!")

confirm_apartment_handler = CallbackQueryHandler(
    confirm_apartment_callback,
    pattern=r"^confirm_apartment_\d+$"
)