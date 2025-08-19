from handlers.RegistrationHandler import registration_conversation
from handlers.AddObjectHandler import add_object_conv
from handlers.ObjectCommitHandler import confirm_apartment_handler
from handlers.ObjectRedoHandler import redo_apartment_handler
from handlers.SearchParamsCollectionHandler import search_conv
from handlers.CommitDeclineCancelBookingHandler import conv_commit_decline_cancel
from handlers.BookingChatHandler import booking_chat
from handlers.UserSendProblemHandler import problem_handler
from handlers.AdminReplayUserProblemHandler import admin_replay_handler
#from handlers.UnknownComandHandler import unknown_command_handler
from handlers.GlobalCommands import cancel_command
from handlers.BookingChatConversation import exit_booking_chat
from handlers.ShowInfoHandler import info_callback_handler, info_command


from db_monitor import check_db
from booking_expired_monitor import check_expired_booking
from booking_complit_monitor import check_complit_booking
from booking_placeholder_monitor import check_placeholder_booking

import os
from pathlib import Path
from datetime import time

from utils.logging_config import setup_logging, log_function_call, get_logger

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
    filters,
    CallbackQueryHandler,
    ApplicationBuilder,
    JobQueue
)
# Initialize comprehensive logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_dir=os.getenv("LOG_DIR", "/app/logs"),
    enable_console=True,
    enable_file=True
)

logger = get_logger(__name__)

async def post_init(application: Application) -> None:
    # Настройка меню команд (синяя плашка)
    commands = [
        BotCommand("start", "🔄 Перезапустить бот"),
        BotCommand("help", "⚠️ Помощь"),
        BotCommand('info', "📌 Инструкция"),
        BotCommand("cancel", "⛔ Отмена")

    ]
    await application.bot.set_my_commands(commands)

        # Запуск периодических задач
    application.job_queue.run_repeating(
        check_expired_booking,
        interval=60 * 60,
        first=5
    )
    application.job_queue.run_repeating(
        check_db,
        interval=30 * 60,
        first=10
    )
    application.job_queue.run_daily(
        check_complit_booking,
        time(hour=1, minute=19)
    )
    application.job_queue.run_daily(
        check_placeholder_booking,
        time(hour=1, minute=9)
    )


def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in .env")


    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    #глобальные обработчики
    app.add_handler(CommandHandler("info",info_command), group=0)
    app.add_handler(problem_handler, group=0)
    app.add_handler(admin_replay_handler,group=0)

    #админские обработки
    app.add_handler(
        CallbackQueryHandler(info_callback_handler, pattern=r"^info_"),
        group=1
    )
    #app.add_handler(unknown_command_handler,group=0) #обработчик незнакомых команд
    
    # Регистрируем хендлеры
    
    app.add_handler(registration_conversation,group=1) #процесс регистрации (users, sessions), выбор роли

    app.add_handler(add_object_conv,group=1) #процесс создания объекта бронирования

    app.add_handler(confirm_apartment_handler,group=1) #проверка и подтверждение создания объекта

    app.add_handler(redo_apartment_handler,group=1) #отмена создания объекта

    app.add_handler(search_conv,group=1) #процесс выбора квартиры для бронирования

    app.add_handler(conv_commit_decline_cancel,group=1) #сценарий, когда бронирование отклонено или отменено

    app.add_handler(booking_chat,group=1)   #обработчик приватных чатов между пользователями
    



    





    # Без asyncio
    app.run_polling()

if __name__ == "__main__":

    main()
