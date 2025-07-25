from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, MessageHandler, filters

from db.db_async import get_async_session
from db.models.users import User
from sqlalchemy import select, update
from db.models.sessions import Session

from bot.handlers.location_request import ask_location


async def handle_phone_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user_id = update.effective_user.id
    role_id = context.user_data.get("role_id")


    async with get_async_session() as session:
        result = await session.execute(
              select(User).where(
            (User.tg_user_id == tg_user_id) &
            (User.role_id == role_id)
        )
        )
        user = result.scalars().first()

        if not user:
            await update.message.reply_text("Пользователь не найден в базе.")
            return
        

        # Если пользователь отправил контакт
        if update.message.contact:
            phone_number = update.message.contact.phone_number
            user.phone_number = phone_number
            await session.commit()
            await update.message.reply_text("Спасибо! Номер сохранён.",
                reply_markup=ReplyKeyboardRemove()
                )
            
            await ask_location(update, context)
            return
            

        # Если пользователь выбрал «Отклонить»
        if update.message.text == "Отклонить":
            # Можно сохранить отказ в БД (например, is_phone_declined=True)
            #user.phone_number = None  # если вдруг был
            await session.commit()
            await update.message.reply_text("OK")

            await ask_location(update, context)
            return

    
# Экспортируем хендлер
phone_save_handler = MessageHandler(filters.CONTACT, handle_phone_response)
phone_decline_handler = MessageHandler(filters.TEXT & filters.Regex("^Отклонить$"), handle_phone_response)

