
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)

from utils.referral_link import (
    check_or_create_source, 
    get_referral_stats, 
    validate_suffix,
    validate_unique_suffix,
    generate_unique_suffix
)
from utils.message_tricks import add_message_to_cleanup, cleanup_messages, send_message

from utils.logging_config import (
    structured_logger, 
    log_db_select, 
    log_db_insert, 
    log_db_update,
    log_db_delete,
    LoggingContext,
    monitor_performance
)

# Состояния
(CREATE_LINK, 
HANDLE_BUTTONS) = range(2)

async def start_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user_id = update.effective_user.id

    source = await check_or_create_source(tg_user_id)
    print(f"DEBUG_REFERRAL_LINK:{source}")
    if source:  # уже есть ссылка
        stats = await get_referral_stats(source.id)
        msg = (
            f"💰 Ваша реферальная ссылка:\n"
            f"https://t.me/{context.bot.username}?start={source.suffix}\n\n"
            f"👥 <u>Регистраций по вашей ссылке: {stats['registrations']}</u>\n\n"
            f"🏡 Ваши гости добавили объектов: <b>{stats['apartments']}</b>\n"
            f"📅 Совершено бронирований: <b>{stats['appts_bookings']}</b>\n"
            f"💳 На сумму: <b>{stats['appts_amount']}</b> ₽\n"
            f"🏆 Ваше вознаграждение: <b>{stats['appts_reward']}</b> ₽\n\n"
            f"🏡 Ваши гости совершили бронирований: <b>{stats['renter_bookings']}</b>\n"
            f"💳 На сумму: <b>{stats['renter_amount']}</b> ₽\n"
            f"🏆 Ваше вознаграждение: <b>{stats['appts_reward']}</b> ₽"
        )
        msg = await send_message(update, msg, parse_mode = "HTML")
        await add_message_to_cleanup(context,msg.chat_id,msg.message_id)
        return ConversationHandler.END

    # Если ссылки нет — показываем условия
    text = (
        "📜 Условия участия в программе:\n"
        "1. Вы получаете реферальную ссылку;\n"
        "2. Распространяете ссылку любым законным способом;\n"
        "3. За действия приглашённых пользователей получаете вознаграждение:\n"
        " - 1,5% от суммы сделки за бронирование, в котором приглашенный пользователь является Арендатором;\n"
        " - 1,5% от суммы сделки за бронирование, в котором приглашенный пользователь является Арендодателем;\n"
        "4. Вознаграждение выплачивается переводом на карту 30 числа каждого месяца за бронирования, завершенные не позднее 24 числа этого месяца включительно;\n"
        "5. Организатор программы вправе изменить условия в любое время;\n"
        "6. В случае изменения условий вам будет направлено уведомление.\n"
        "7. После нажатия на кнопку <b>Принять</b> ваша ссылка будет сгенерирована автоматически.\n\n"
        "👑<b>Хотите продолжить?</b>👑"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Принять", callback_data="accept_terms"),
        InlineKeyboardButton("❌ Отклонить", callback_data="decline_terms")]
    ]
    msg = await send_message(update, text, reply_markup=InlineKeyboardMarkup(keyboard),parse_mode='HTML')
    await add_message_to_cleanup(context,msg.chat_id,msg.message_id)
    return CREATE_LINK

async def handle_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    print(f"DEBUG_REFFERAL_COND: {query.data}")
    if query.data == "decline_terms":
        await query.edit_message_text("🚫 Вы отказались от участия в программе.")
        return ConversationHandler.END
    
    tg_user_id = update.effective_user.id
    with LoggingContext("registration_name_step", user_id=tg_user_id) as log_ctx:
        try:
            suffix = await generate_unique_suffix(tg_user_id, update.effective_user.username, update.effective_user.first_name)
             
            structured_logger.info(
                "Suffix creation",
                user_id=tg_user_id,
                action="suffix creation",
                context={
                    'name_length': len(suffix),
                    'suffix': suffix[:50]
                }
            )
        except Exception as e:
            structured_logger.error(
                f"Error in handle_suffix_request: {str(e)}",
                user_id=tg_user_id,
                action="referral_link_error",
                exception=e
            )
            await update.message.reply_text("Ошибка при создании суффикса.")
            return CREATE_LINK


    source = await check_or_create_source(tg_user_id, suffix)

    # Убираем кнопки с предыдущего сообщения
    await query.edit_message_reply_markup(reply_markup=None)

    # Отправка готовой ссылки пользователю
    link = f"https://t.me/{context.bot.username}?start={source.suffix}"

    context.user_data["link"] = link

    msg_text = (
        f"✅ Ваша реферальная ссылка:\n"
        f"{link}"
    )
    keyboard = [
        [InlineKeyboardButton("Скопировать ссылку", callback_data="copy_link"),
         InlineKeyboardButton("В главное меню", callback_data="back_menu")]
    ]
    # Обязательно используем query.message.chat_id
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=msg_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return HANDLE_BUTTONS

async def handle_link_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data == "copy_link":
        # показываем ссылку во всплывающем алерте
        await query.answer(
            text=f"{context.user_data.get('link')}",
            show_alert=True
        )
    elif query.data == "back_menu":
        await query.answer()  # убираем крутилку
            # Это удалит клавиатуру под исходным сообщением
        await query.edit_message_reply_markup(reply_markup=None)
        await cleanup_messages(context)
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена"""
    await cleanup_messages(context)
    context.user_data.clear()
    await update.message.reply_text("❌ Отмена. Вы сможете вернуться к созданию реферальной ссылки позднее",reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END
