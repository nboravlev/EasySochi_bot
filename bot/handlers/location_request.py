from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from db.db_async import get_async_session
from db.models.users import User

request_location_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧭 Поделиться гео", request_location=True)],
        [KeyboardButton(text="Отклонить")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Пожалуйста, отправьте свое гео для улучшения поиска.",
        reply_markup=request_location_keyboard
    )