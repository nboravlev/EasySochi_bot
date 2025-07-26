from db.db_async import get_async_session
from db.models.apartments import Apartment

from telegram.ext import ContextTypes,CallbackQueryHandler

from sqlalchemy import select, delete

from telegram import Update

#from bot.handlers.AddObjectHandler import ADDRESS_INPUT

async def redo_apartment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    apartment_id = int(update.callback_query.data.split("_")[-1])
    async with get_async_session() as session:
        await session.execute(delete(Apartment).where(Apartment.id == apartment_id))
        await session.commit()

    await update.callback_query.edit_message_text("🚫 Данные удалены. Начнём заново /add_object")
    
    #return ADDRESS_INPUT

redo_apartment_handler = CallbackQueryHandler(
    redo_apartment_callback,
    pattern=r"^redo_apartment_\d+$"
)