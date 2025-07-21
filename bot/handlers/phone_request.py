from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from db.db_async import get_async_session
from db.models.users import User

request_phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📞 Поделиться номером", request_contact=True)],
        [KeyboardButton(text="Отклонить")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

async def ask_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Пожалуйста, отправьте свой номер телефона.",
        reply_markup=request_phone_keyboard
    )
