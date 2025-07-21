from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from bot.handlers.user_session import register_user_and_session
from bot.handlers.phone_request import ask_phone_number  
from bot.handlers.location_request import ask_location


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Вызывается при /start.
    Регистрирует пользователя и создаёт сессию.
    """
    tg_user = update.effective_user
    bot_id = context.bot.id
   

    user, session = await register_user_and_session(tg_user, bot_id)

   

    # 👇 Проверка: если телефона нет — запрашиваем
    if not user.phone_number:
        await ask_phone_number(update, context)
    else:
        await update.message.reply_text("Ваш номер уже есть в базе.")
        # Можно сразу перейти к следующему шагу
        await ask_location(update, context)


    print(f"Получена команда /start от пользователя {update.effective_user.id}")
    #await update.message.reply_text("Привет! Бот работает.")
"""
    # вспомогательный текст :)
    text = (
        f"Привет, {user.first_name}!\n"
        f"Ваша сессия #{session.id} начата — давайте бронировать жильё."
    )
    await update.message.reply_text(text)
"""
# Экспортируем хендлер
start_handler = CommandHandler("start", start_command)
