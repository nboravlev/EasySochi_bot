from telegram.ext import ApplicationBuilder, JobQueue
from bot.handlers.RegistrationHandler import registration_conversation
from bot.handlers.AddObjectHandler import add_object_conv
from bot.handlers.ObjectCommitHandler import confirm_apartment_handler
from bot.handlers.ObjectRedoHandler import redo_apartment_handler
from bot.handlers.SearchParamsCollectionHandler import search_conv
import os
from pathlib import Path
from dotenv import load_dotenv


def main():
    # Загрузка .env
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in .env")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрируем хендлеры
    
    app.add_handler(registration_conversation)

    app.add_handler(add_object_conv)

    app.add_handler(confirm_apartment_handler)

    app.add_handler(redo_apartment_handler)

    app.add_handler(search_conv)

    


    





    # Без asyncio
    app.run_polling()

if __name__ == "__main__":
    main()
