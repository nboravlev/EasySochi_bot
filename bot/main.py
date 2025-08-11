from telegram.ext import ApplicationBuilder, JobQueue
from handlers.RegistrationHandler import registration_conversation
from handlers.AddObjectHandler import add_object_conv
from handlers.ObjectCommitHandler import confirm_apartment_handler
from handlers.ObjectRedoHandler import redo_apartment_handler
from handlers.SearchParamsCollectionHandler import search_conv
from handlers.CommitDeclineCancelBookingHandler import conv_commit_decline_cancel
from handlers.BookingChatHandler import booking_chat
import os
from pathlib import Path

import os

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    BotCommand,
    BotCommandScopeChat
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)


async def post_init(application: Application) -> None:
    # Настройка меню команд (синяя плашка)
    commands = [
        BotCommand("start", "🚀 Перезапустить бот"),
        BotCommand("help", "🚨 Помощь"),
        BotCommand("cancel", "⛔ Отменить действие"),
        BotCommand('exit_chat', "☎️ Прервать чат с пользователем")
    ]
    await application.bot.set_my_commands(commands)

def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in .env")


    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()



    # Регистрируем хендлеры
    
    app.add_handler(registration_conversation) #процесс регистрации (users, sessions), выбор роли

    app.add_handler(add_object_conv) #процесс создания объекта бронирования

    app.add_handler(confirm_apartment_handler) #проверка и подтверждение создания объекта

    app.add_handler(redo_apartment_handler) #отмена создания объекта

    app.add_handler(search_conv) #процесс выбора квартиры для бронирования

    app.add_handler(conv_commit_decline_cancel) #сценарий, когда собственник не подтверждает

    app.add_handler(booking_chat)   #обработчик приватных чатов между пользователями


    





    # Без asyncio
    app.run_polling()

if __name__ == "__main__":
    main()
