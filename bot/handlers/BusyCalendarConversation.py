import datetime
from datetime import date

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InputMediaPhoto,
    KeyboardButton
)
from telegram.ext import (
    ConversationHandler,
    CallbackContext,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
import logging
from decimal import Decimal
from db.db_async import get_async_session

from utils.keyboard_builder import build_calendar, CB_NAV, CB_SELECT
from utils.escape import safe_html
from utils.message_tricks import add_message_to_cleanup, cleanup_messages

from db.models import Session, Booking


from sqlalchemy import update as sa_update, select 
from sqlalchemy.orm import selectinload



# Состояния диалога
(HANDLE_PLACEHOLDER_BEGIN,
HANDLE_PLACEHOLDER_END,
COMMIT_PLACEHOLDER)= range(3)

PLACEHOLDER_BOOKING_STATUS = 7

async def placeholder_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    apartment_id = int(query.data.split("_")[-1])
    target_chat = query.message.chat_id

    context.user_data["start_date"] = None
    context.user_data["end_date"] = None
    context.user_data["apartment_id"] = apartment_id
    #await cleanup_messages(context)
        # Отправляем новое сообщение с календарём
    msg = await context.bot.send_message(
        chat_id = target_chat,
        text="📅 Дата начала блокировки:",
        reply_markup=build_calendar(date.today().year, date.today().month)
    )
    await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
    return HANDLE_PLACEHOLDER_BEGIN

async def calendar_callback(update: Update, context: CallbackContext):
    """Обработка нажатий календаря"""
    query = update.callback_query
    await query.answer()
    data = query.data

    start_date = context.user_data.get("start_date")
    end_date = context.user_data.get("end_date")

    # Навигация по месяцам
    if data.startswith(CB_NAV):
        _, y, m = data.split(":")
        y, m = int(y), int(m)
        msg = await query.edit_message_reply_markup(
            reply_markup=build_calendar(y, m, start_date, end_date)
        )
        await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
        return HANDLE_PLACEHOLDER_BEGIN if not start_date else HANDLE_PLACEHOLDER_END

    # Выбор даты
    if data.startswith(CB_SELECT):
        try:
            _, d = data.split(":")
            selected_date = date.fromisoformat(d)
        except Exception as e:
            print(f"[ERROR] Некорректная дата из callback: {data}, {e}")
            await query.answer("⚠️ Ошибка выбора даты. Попробуйте снова", show_alert=True)
            await update.message.reply_text("Ошибка при выборе даты.")
            return HANDLE_PLACEHOLDER_BEGIN

        # ✅ Проверяем, выбрал ли пользователь check-in
        if start_date is None:
            # ✅ Сохраняем дату заезда
            context.user_data["start_date"] = selected_date
            await query.edit_message_text(
                f"🔒 Блокировка с: {selected_date}\nВыберите дату снятия блока",
                reply_markup=build_calendar(selected_date.year, selected_date.month, check_in=selected_date) #функция клавиатуры календаря ждет параметр с именем check_in
            )
            return HANDLE_PLACEHOLDER_END
        # Если уже выбрали check-in, проверяем check-out
        if selected_date <= start_date:
            await query.answer("⛔ Дата выезда должна быть позже заезда", show_alert=True)
            return HANDLE_PLACEHOLDER_END

        context.user_data["end_date"] = selected_date

                # Кнопки подтверждения
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="commit_placeholder"),
            InlineKeyboardButton("🔄 Начать заново", callback_data=f"placeholder_{context.user_data['apartment_id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        msg = await query.edit_message_text(
            f"🟡 Проверьте даты блокировки:\n"
            f"📅 {start_date} → {selected_date}",
            reply_markup=reply_markup
        )
        await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
        return COMMIT_PLACEHOLDER

async def handle_placeholder_commit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    apartment_id = context.user_data.get("apartment_id")
    start_date = context.user_data.get("start_date")
    end_date = context.user_data.get("end_date")

    if not (apartment_id and start_date and end_date):
        await query.edit_message_text("⚠️ Ошибка: данные заглушки неполные. Попробуйте заново.")
        return HANDLE_PLACEHOLDER_BEGIN

    # ✅ Создаём заглушку в БД
    async with get_async_session() as session:
        booking = Booking(
            tg_user_id=user_id,
            apartment_id=apartment_id,
            status_id=PLACEHOLDER_BOOKING_STATUS,
            check_in=start_date,
            check_out=end_date,
            guest_count=7,
            total_price=Decimal("0.00"),
            comments="Заглушка (блокировка календаря)",
            is_active=True
        )
        session.add(booking)
        await session.commit()

    # 🔄 Показываем сообщение пользователю
    keyboard = [
        [InlineKeyboardButton("➕ Добавить", callback_data=f"placeholder_{apartment_id}"),
        InlineKeyboardButton("🔙 В меню", callback_data="back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = await query.edit_message_text(
        f"🔒 Блокировка для квартиры #{apartment_id} успешно создана\n"
        f"📅 {start_date} → {end_date}",
        reply_markup=reply_markup
    )
    await add_message_to_cleanup(context, msg.chat_id, msg.message_id)

    return ConversationHandler.END

# === Отмена ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):    
    await update.message.reply_text(
        "❌ Действие отменено. Для продолжения работы нажмите /start",
        reply_markup=ReplyKeyboardRemove()
    )
    await cleanup_messages(context)
    context.user_data.clear()
    return ConversationHandler.END
