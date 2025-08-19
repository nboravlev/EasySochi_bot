from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, ConversationHandler, ApplicationHandlerStop, CallbackQueryHandler

from utils.logging_config import log_function_call, LogExecutionTime, get_logger

import os

logger = get_logger(__name__)

INFO_TEXTS = {
    "info_booking": {
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
    "info_object": {
        "title": "🏠 *Инструкция по добавлению объекта:*",
        "body": (
            "1. Перейдите в раздел 'Хочу сдавать жильё';\n"
            "2. Следуйте подсказкам робота;\n"
            "3. Заполните название, описание, фото и т.д.;\n"
            "4. При вводе адреса укажите город, улицу и номер дома;\n"
            "5. Внимание! В поисковой выдаче демонстрируется одно фото - первое загруженное;\n"
            "6. Подтвердите или введите заново, если нужно;\n"
            "7. После создания заявки на ваш объект вы получите уведомление;\n"
            "8. В течение суток подтвердите или отклоните его;\n"
            "9. После подтверждения у пользователя появится чат с вами;\n"
            "10. Проинструктируйте пользователя по оплате и заселению в чате;\n"
            "11. В разделе 'Мои объекты' просматривайте ваши объекты и созданные на них заявки;\n"
            "12. Редактирование пока не доступно (только удалить/создать заново);\n"
            "13. Если есть активные брони — не даст удалить, пишите в 'Помощь';\n"
            "14. Чтобы скрыть объект из поиска на занятые даты — самостоятельно создайте и подтвердите бронирование на даты;\n"
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


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает меню справки. Работает как при прямом вызове /info, так и при callback.
    """
    message = _get_effective_message(update)
    if not message:
        return

    keyboard = [
        [InlineKeyboardButton("📆 Инструкция по бронированию", callback_data="info_booking")],
        [InlineKeyboardButton("🏠 Инструкция по добавлению объекта", callback_data="info_object")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("ℹ️ Выберите инструкцию:", reply_markup=reply_markup)


async def show_info_text(update_or_query: Update, key: str):
    """
    Выводит справочный текст по ключу. Работает и для обычных сообщений, и для callback.
    Кнопка 'Назад в инфо' имеет callback_data='help_menu'.
    """
    data = INFO_TEXTS.get(key)
    if not data:
        return

    text = f"{data['title']}\n\n{data['body']}"
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Назад в инфо", callback_data="info_menu")]]
    )

    message = _get_effective_message(update_or_query)
    if not message:
        return

    # Можно использовать edit_message_text если вы хотите заменить предыдущую карточку,
    # но reply_text достаточно универсален.
    await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def info_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    if data == "info_booking":
        await show_info_text(update, "info_booking")
    elif data == "info_object":
        await show_info_text(update, "info_object")
    elif data == "info_menu":
        await info_command(update, context)
    else:
        return