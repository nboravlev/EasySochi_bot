from telegram.ext import ApplicationBuilder
from bot.handlers.start import start_handler
from bot.handlers.phone_save import phone_save_handler, phone_decline_handler
from bot.handlers.location_save import location_save_handler, location_decline_handler
from bot.handlers.role_save import role_handler
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

    
    app.add_handler(phone_save_handler)

    app.add_handler(phone_decline_handler)

    app.add_handler(location_save_handler)

    app.add_handler(location_decline_handler)

    app.add_handler (role_handler)

    





    # Без asyncio
    app.run_polling()

if __name__ == "__main__":
    main()
