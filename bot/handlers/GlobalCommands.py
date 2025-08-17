from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, ConversationHandler, ApplicationHandlerStop, CallbackQueryHandler

from utils.logging_config import log_function_call, LogExecutionTime, get_logger

import os
def _make_admin_message(user, problem_text: str) -> str:
    text = (
        f"🚨 *Сообщение о проблеме*\n\n"
        f"👤 Пользователь: [{user.first_name}](tg://user?id={user.id})\n"
        f"🆔 TG ID: `{user.id}`\n\n"
        f"📝 Проблема:\n{problem_text}"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{user.id}")]
    ])
    return text, keyboard

@log_function_call(action="start_problem")
async def start_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Вызывается по /help (глобально) или как fallback.
    Ставит флаг ожидания и просит пользователя описать проблему.
    """
    logger = get_logger(__name__)
    user = update.effective_user
    logger.info("User %s started reporting a problem", user.id)
    logger.info("context = %r", context)
    logger.info("context.user_data = %r", getattr(context, "user_data", None))
    # Отметим, что ждём описания проблемы
    context.user_data["awaiting_problem"] = True

    # Сообщение пользователю
    await update.message.reply_text(
        "⚠️ Опишите ситуацию, и я передам сообщение администратору.\n\n"

    )
    # Не возвращаем ConversationHandler.END — просто выходим; флаг решает поведение
    return None

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

@log_function_call(action="process_problem")
async def process_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Формирует и отправляет сообщение админам; очищает флаг.
    """
    logger = get_logger(__name__)
    if not ADMIN_CHAT_ID:
        logger.error("ADMIN_CHAT_ID not set")
        await update.message.reply_text("Ошибка конфигурации (нет ADMIN_CHAT_ID).")
        return

    user = update.effective_user
    problem_text = update.message.text.strip() if update.message else ""
    admin_message, keyboard = _make_admin_message(user, problem_text)
    chat = await context.bot.get_chat(ADMIN_CHAT_ID)
    print(f"DEBUG_статус_бота: {chat}")
    # Отправляем админу
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_message,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    # Ответ пользователю
    await update.message.reply_text("✅ Сообщение передано администратору. Спасибо!")

    # Снимаем флаг ожидания (важно)
    context.user_data.pop("awaiting_problem", None)


    # мы не знаем, в каком состоянии был пользователь; обычно оставляем его там же.
    return None

async def reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    print (f"DEBUG Admin_replay: {query.data}")
    # user_id зашит в callback_data
    _, user_id_str = query.data.split("_")
    target_user_id = int(user_id_str)
    
    # Сохраняем, кому хотим ответить
    context.user_data["reply_to_user"] = target_user_id

    # Предлагаем админу ввести текст ответа

    await query.message.reply_text(
        f"✍️ Введите сообщение для пользователя {target_user_id}:"
    )


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user_id = context.user_data.get("reply_to_user")
    if not target_user_id:
        await update.message.reply_text("❌ Ошибка: нет пользователя для ответа.")
        return

    reply_text = update.message.text.strip()

    # Отправляем пользователю
    await context.bot.send_message(
        chat_id=target_user_id,
        text=f"📩 Ответ администратора:\n\n{reply_text}"
    )

    # Подтверждаем админу
    await update.message.reply_text("✅ Ответ отправлен пользователю.")

    # Стираем временные данные
    context.user_data.pop("reply_to_user", None)



@log_function_call(action="global_text_router")
async def handle_global_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Глобальный перехватчик для текстовых сообщений.
    Если установлен флаг awaiting_problem -> обрабатываем как проблему.
    Если установлен флаг reply_to_user -> обрабатываем как ответ админа.
    Иначе — возвращаем None (пропускаем дальше).
    """
    if not update.message:
        return

    logger = get_logger(__name__)
    user_data = getattr(context, "user_data", None) or {}

    # Check if the user is an admin replying to a user
    if user_data.get("reply_to_user"):
        # Process the admin's message as a reply
        await handle_admin_reply(update, context)
        # Raise ApplicationHandlerStop to prevent other handlers from firing
        raise ApplicationHandlerStop

    # Check if a regular user is reporting a problem
    if user_data.get("awaiting_problem"):
        await process_problem(update, context)
        raise ApplicationHandlerStop
    
    # Otherwise, do nothing and let other handlers process the message
    return None

HELP_TEXTS = {
    "help_booking": {
        "title": "📆 *Инструкция по бронированию:*",
        "body": (
            "1. Перейдите в раздел 'Хочу снять жильё';\n"
            "2. Следуйте подсказкам робота;\n"
            "3. Найдите подходящий объект через поиск;\n"
            "4. Нажмите 'Забронировать';\n"
            "5. Дождитесь подтверждения от владельца;\n"
            "6. Общайтесь с ним в чате по бронированию;\n"
            "7. Запросите инструкции по оплате и заселению;\n"
            "8. Все заявки сохраняются в разделе 'Мои бронирования';\n"
            "9. Из своей заявки можно вызвать чат с владельцем;\n"
            "10. Если возникнут трудности, напишите в раздел 'Помощь'."
        )
    },
    "help_object": {
        "title": "🏠 *Инструкция по добавлению объекта:*",
        "body": (
            "1. Перейдите в раздел 'Хочу сдавать жильё';\n"
            "2. Следуйте подсказкам робота;\n"
            "3. Заполните название, описание, фото и т.д.;\n"
            "4. При вводе адреса укажите город, улицу и номер дома;\n"
            "5. В поиске показывается первое загруженное фото;\n"
            "6. Подтвердите или введите заново, если нужно;\n"
            "7. После создания бронирования вы получите уведомление;\n"
            "8. В течение суток подтвердите или отклоните его;\n"
            "9. После подтверждения у пользователя появится чат с вами;\n"
            "10. По оплате и заселению вы инструктируете сами в чате;\n"
            "11. В разделе 'Мои объекты' можно просматривать ваши объекты и созданные на них заявки;\n"
            "12. Редактирование пока не доступно (только удалить/создать заново);\n"
            "13. Если есть активные брони — не даст удалить, пишите в 'Помощь';\n"
            "14. Чтобы скрыть объект из поиска на занятые даты — самостоятельно создайте и подтвердите бронирование;\n"
            "15. 25 числа месяца приходит напоминание об оплате комиссии за бота."
        )
    }
}


def _get_effective_message(update: Update):
    """
    Возвращает message-объект, независимо от того, пришло ли это update.message
    или это callback_query (update.callback_query.message).
    """
    if update.message:
        return update.message
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return None


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает меню справки. Работает как при прямом вызове /info, так и при callback.
    """
    message = _get_effective_message(update)
    if not message:
        return

    keyboard = [
        [InlineKeyboardButton("📆 Инструкция по бронированию", callback_data="help_booking")],
        [InlineKeyboardButton("🏠 Инструкция по добавлению объекта", callback_data="help_object")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("ℹ️ Выберите инструкцию:", reply_markup=reply_markup)


async def show_help_text(update_or_query: Update, key: str):
    """
    Выводит справочный текст по ключу. Работает и для обычных сообщений, и для callback.
    Кнопка 'Назад в инфо' имеет callback_data='help_menu'.
    """
    data = HELP_TEXTS.get(key)
    if not data:
        return

    text = f"{data['title']}\n\n{data['body']}"
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Назад в инфо", callback_data="help_menu")]]
    )

    message = _get_effective_message(update_or_query)
    if not message:
        return

    # Можно использовать edit_message_text если вы хотите заменить предыдущую карточку,
    # но reply_text достаточно универсален.
    await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def help_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик callback'ов для help_*
    - отвечает на query (query.answer())
    - вызывает show_help_text или возвращает в меню вызовом help_command
    """
    query = update.callback_query
    if not query:
        return

    await query.answer()  # убираем "крутилку" в UI

    data = query.data or ""
    if data == "help_booking":
        await show_help_text(update, "help_booking")
    elif data == "help_object":
        await show_help_text(update, "help_object")
    elif data == "help_menu":
        await help_command(update, context)
    else:
        return

    
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⛔ Вы остановили бота. Чтобы возобновить работу нажмите /start")
    context.user_data.clear()
    return ConversationHandler.END