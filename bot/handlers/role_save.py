from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.handlers.user_session import register_user_and_session
from bot.handlers.phone_request import ask_phone_number
from bot.handlers.location_request import ask_location

ROLE_MAPPING = {
    "🏠 Хочу арендовать жильё": 1,
    "🏘 Хочу предложить объект": 2
}

async def handle_role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    user_choice = update.message.text
    role_id = ROLE_MAPPING.get(user_choice)
    
    tg_user = update.effective_user
    bot_id = context.bot.id
    

    if role_id is None:
        await update.message.reply_text("Пожалуйста, выберите один из вариантов на клавиатуре.")
        return
    
    context.user_data["role_id"] = role_id
    print(f"выбрана роль: {role_id}")
    user, new_session, is_new_user = await register_user_and_session(tg_user, bot_id, role_id)

    context.user_data["is_new_user"] = is_new_user
    

    # Сохраняем session_id, если нужно
    context.user_data["session_id"] = new_session.id
    print(f"session_id: {new_session.id}")

    if not user.phone_number:
        await update.message.reply_text("Спасибо! Вы выбрали роль.",
                                        reply_markup=ReplyKeyboardRemove())
        await ask_phone_number(update, context)
    else:
        await update.message.reply_text("Ваш номер уже есть в базе.",
                                        reply_markup=ReplyKeyboardRemove())
        await ask_location(update, context)

# Хендлер (экспортируем)
role_handler = MessageHandler(filters.TEXT & filters.Regex("^(🏠 Хочу арендовать жильё|🏘 Хочу предложить объект)$"), handle_role_selection)
