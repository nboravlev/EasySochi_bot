from telegram.ext import ApplicationBuilder
from bot.handlers.start import start_handler

import os
from pathlib import Path
from dotenv import load_dotenv



def main():
    # Загрузка .env
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in .env")

    # Создаём объект приложения
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрируем хендлеры
    app.add_handler(start_handler)

    print("Бот запущен. Ожидаю команды /start...")

    # Без asyncio
    app.run_polling()

if __name__ == "__main__":
    main()
