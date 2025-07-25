from sqlalchemy import select, update
from telegram import Update
from db.db_async import get_async_session
from telegram.ext import ContextTypes
from bot.handlers.AddObjectConversation import start_add_object



async def proceed_after_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role_id = context.user_data.get("role_id")

    if role_id == 1:
        await update.message.reply_text("Вы выбрали аренду. Давайте подберем жильё по вашим параметрам!")
        #await start_rent_flow(update, context)

    elif role_id == 2:
        await update.message.reply_text(
            "Вы выбрали добавление объекта. Давайте внесем информацию о вашей недвижимости.\n"
            "Нажмите /add_object, чтобы начать."
        )


    else:
        await update.message.reply_text("Неизвестная роль. Пожалуйста, начните заново.")
