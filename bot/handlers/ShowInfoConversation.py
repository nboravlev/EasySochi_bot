from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
from utils.message_tricks import add_message_to_cleanup, cleanup_messages, send_message
from handlers.ReferralLinkConversation import start_invite
from handlers.UserSendProblemConversation import start_problem

from telegram.error import BadRequest #временная замена моему логгеру
import logging   #временная замена моему логгеру
import os



INFO_TEXTS = {
    "info_booking": {
        "title": "📆 *Инструкция по бронированию:*",
        "body": (
            "1. Перейдите в раздел <b>Хочу снять жильё</b>;\n"
            "2. Следуйте подсказкам робота;\n"
            "3. Найдите подходящий объект через поиск;\n"
            "4. Нажмите <b>Забронировать</b>;\n"
            "5. Дождитесь подтверждения от собственника;\n"
            "6. Общайтесь с ним в чате по бронированию;\n"
            "7. Запросите инструкции по оплате и заселению;\n"
            "8. Все заявки сохраняются в разделе <b>Мои бронирования</b>;\n"
            "9. Из своей заявки можно вызвать чат с владельцем;\n"
            "10. Если возникнут трудности, напишите в раздел /help."
        )
    },
    "info_object": {
        "title": "🏠 *Инструкция по добавлению объекта:*",
        "body": (
            "1. Перейдите в раздел <b>Хочу сдавать жильё</b>;\n"
            "2. Следуйте подсказкам робота;\n"
            "3. Заполните название, описание, фото и т.д.;\n"
            "4. При вводе адреса укажите город, улицу и номер дома;\n"
            "5. Внимание! В поисковой выдаче демонстрируется одно фото - первое загруженное;\n"
            "6. Подтвердите или введите заново, если нужно;\n"
            "7. После создания заявки на ваш объект вы получите уведомление;\n"
            "8. В течение суток подтвердите или отклоните его;\n"
            "9. После подтверждения у пользователя появится чат с вами;\n"
            "10. Проинструктируйте пользователя по оплате и заселению в чате;\n"
            "11. В блоке <b>Мои объекты</> просматривайте ваши объекты и созданные на них заявки;\n"
            "12. Доступно редактирование цены. Другие изменения по запросу или через Удалить/создать заново;\n"
            "13. Если есть активные брони — не даст удалить, пишите в /help;\n"
            "14. Чтобы скрыть объект из поиска на занятые даты — используйте <b>Мои Объекты/Календарь занятости</b>;\n"
            "15. 25 числа месяца приходит напоминание об оплате комиссии за бота."
        )
    },
    "info_terms":{
        "title": "📜 *Условия использования сервиса EasySochi_rent_bot*",
        "body": (
                "1. EasySochi является информационным сервисом (чат-ботом) и не является стороной сделок аренды.\n"
                "2. Сервис предоставляет платформу для коммуникации между собственниками жилья и пользователями (арендаторами).\n"
                "3. Ответственность за достоверность информации (описания, фото, цены, условия) несёт лицо, её разместившее.\n"
                "4. Все договорённости по аренде, оплате и заселению заключаются напрямую между собственником и пользователем.\n"
                "5. EasySochi не контролирует и не гарантирует выполнение обязательств сторон.\n"
                "6. Сервис стремится обеспечивать бесперебойную работу чат-бота, но не несёт ответственности за перебои связи или недоступность Telegram.\n"
                "7. Пользователи предоставляют свои персональные данные, данные объектов и иную информацию добровольно.\n"
                "8. Обработка данных осуществляется только в объёме, необходимом для работы сервиса (регистрация, поиск, бронирование, уведомления).\n"
                "9. EasySochi обязуется не передавать данные третьим лицам, кроме случаев, предусмотренных законом.\n"
                "10. Используя сервис, пользователь подтверждает, что ознакомлен с данными условиями и принимает их.\n"

        )
    }
}
INFO_HANDLER = 1

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cleanup_messages(context)
    """
    Показывает меню справки. Работает как при прямом вызове /info, так и при callback.
    """
    text = "ℹ️ Выберите инструкцию:"
    keyboard = [
        [InlineKeyboardButton("👥 Арендаторам", callback_data="info_booking"),
         InlineKeyboardButton("Правила сервиса 📜", callback_data="info_terms")],
        [InlineKeyboardButton("🏠 Собственникам", callback_data="info_object"),
         InlineKeyboardButton("В главное меню ➡️", callback_data="back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = await send_message(update,text, reply_markup=reply_markup)
    await add_message_to_cleanup(context,msg.chat_id,msg.message_id)
    return INFO_HANDLER

async def show_info_text(update_or_query: Update, context: ContextTypes.DEFAULT_TYPE, key: str,):
    """
    Выводит справочный текст по ключу. Работает и для обычных сообщений, и для callback.
    Кнопка 'Назад в инфо' имеет callback_data='help_menu'.
    """
    data = INFO_TEXTS.get(key)
    if not data:
        return

    text = f"{data['title']}\n\n{data['body']}"
    markup = [
        [InlineKeyboardButton("↩️ Назад в Инфо", callback_data="info_menu"),
         InlineKeyboardButton("В главное меню ➡️", callback_data="back_menu")]
    ]

    message = await send_message(update_or_query,text,reply_markup=InlineKeyboardMarkup(markup),parse_mode="HTML")
    if not message:
        return
    await add_message_to_cleanup(context,message.chat_id,message.message_id)



async def info_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик callback'ов для help_*
    - Отвечает на query (query.answer()) только для callback'ов info_*
    - Для всех остальных callback'ов пропускает апдейт дальше
    """
    query = update.callback_query
    if not query:
        return ConversationHandler.SKIP  # Пропускаем апдейт для MessageHandler

    data = query.data or ""
    if data == "back_menu":
        await query.answer()
        return ConversationHandler.END

    # Обрабатываем только callback'ы, относящиеся к info
    if data.startswith("info_"):
        await query.answer()  # убираем крутилку в UI
        try:
            # Это удалит клавиатуру под исходным сообщением
            await query.edit_message_reply_markup(reply_markup=None)
        except BadRequest as e:
            # например: сообщение уже удалено или недоступно — логируем и продолжаем
            logging.warning("Не удалось убрать inline-клавиатуру: %s", e)

        if data == "info_booking":
            await show_info_text(update, context, "info_booking")
        elif data == "info_object":
            await show_info_text(update, context, "info_object")
        elif data == "info_terms":
            await show_info_text(update, context, "info_terms")
        elif data == "info_menu":
            await info_command(update, context)

            

        # Если мы обработали callback — блокируем дальнейшую обработку
        return INFO_HANDLER
    
async def help_and_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершает диалог и вызывает info_command."""
    await cleanup_messages(context)
    await start_problem(update, context)
    return ConversationHandler.END

async def invite_and_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершает диалог и вызывает info_command."""
    await cleanup_messages(context)
    await start_invite(update, context)
    return ConversationHandler.END



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Выход из блока Инфо.",
        reply_markup=None
    )
    context.user_data.clear()
    return ConversationHandler.END