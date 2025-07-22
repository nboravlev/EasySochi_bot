from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

role_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏠 Хочу арендовать жильё")],
        [KeyboardButton(text="🏘 Хочу предложить объект")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

async def ask_user_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Что вы хотите сделать:",
            reply_markup=role_keyboard
    )
