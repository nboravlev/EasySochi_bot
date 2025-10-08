from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
from utils.message_tricks import add_message_to_cleanup, send_message

async def global_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()  # Ответ на callback, чтобы убрать «часики»
    
    # Удаляем или затираем предыдущее сообщение
    try:
        await query.delete_message()
    except Exception:
        # Если удаление невозможно, просто убираем кнопки
        await query.edit_message_reply_markup(reply_markup=None)

    # Создаем новую кнопку "Показать меню"
    keyboard = [
        [InlineKeyboardButton("📋 Показать меню", callback_data="back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем новое сообщение с инструкцией
    msg_text = "Нажмите для перехода в меню:"
    msg = await send_message(update, msg_text, reply_markup=reply_markup)
    await add_message_to_cleanup(context,msg.chat_id,msg.message_id)

    return ConversationHandler.END
"""   
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("⛔ Вы остановили бота. Чтобы возобновить работу нажмите /start")
    context.user_data.clear()
    return ConversationHandler.END
"""