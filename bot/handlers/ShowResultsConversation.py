from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Шаги диалога
ASK_CHECKIN, ASK_CHECKOUT, APPLY_FILTERS, SHOW_RESULTS, SHOW_DETAILS, CONFIRM_BOOKING = range(6)


async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало поиска: спрашиваем дату заезда"""
    await update.message.reply_text("📅 Выберите дату заезда:")
    # Здесь будет вызов календаря (позже добавим)
    return ASK_CHECKIN


async def set_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Фиксируем дату заезда и запрашиваем дату выезда"""
    context.user_data["check_in"] = update.message.text  # заглушка
    await update.message.reply_text("📅 Теперь выберите дату выезда:")
    return ASK_CHECKOUT


async def set_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Фиксируем дату выезда и переходим к фильтрам"""
    context.user_data["check_out"] = update.message.text  # заглушка
    await update.message.reply_text("Хотите применить фильтры? (Цена / Тип)")
    # позже добавим кнопки для фильтров
    return APPLY_FILTERS


async def apply_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Применение фильтров (пока заглушка) и показ результатов"""
    await update.message.reply_text("🔍 Ищу доступные квартиры...")
    # здесь будет запрос к БД
    await update.message.reply_text("Найдено 5 вариантов. Выберите один для подробностей.")
    # здесь будут кнопки для перехода к деталям
    return SHOW_RESULTS


async def show_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показываем подробную карточку выбранного объекта"""
    apartment_id = update.callback_query.data  # ID объекта
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"🏠 Подробная информация по объекту {apartment_id}")
    # здесь добавим кнопку 'Забронировать'
    return SHOW_DETAILS


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение бронирования"""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("✅ Ваша бронь подтверждена!")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена поиска"""
    await update.message.reply_text("❌ Поиск отменён.")
    return ConversationHandler.END