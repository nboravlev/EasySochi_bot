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
from db.db_async import get_async_session

from utils.calendar_keyboard import build_calendar, CB_NAV, CB_SELECT
from utils.keyboard_builder import build_types_keyboard, build_price_filter_keyboard
from utils.apts_search_session import get_apartments
from utils.booking_navigation_view import booking_apartment_card_full
from utils.booking_complit_view import show_booked_appartment
from utils.escape import safe_html
from utils.request_confirmation import send_booking_request_to_owner
from utils.anti_contact_filter import sanitize_message

from db.models.apartment_types import ApartmentType
from db.models.apartments import Apartment
from db.models.search_sessions import SearchSession
from db.models.bookings import Booking
from db.models.booking_types import BookingType

from sqlalchemy import update as sa_update, select 
from sqlalchemy.orm import selectinload

from utils.logging_config import log_function_call, LogExecutionTime, get_logger

# Состояния диалога
(SELECTING_CHECKIN, 
 SELECTING_CHECKOUT, 
 APTS_TYPES_SELECTION, 
 PRICE_FILTER_SELECTION,
 GUESTS_NUMBER,
 BOOKING_COMMENT)= range(6)

logger = get_logger(__name__)

@log_function_call(action="Start_search_session")
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт поиска жилья: инициализация данных пользователя"""
    # Определяем источник вызова
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        # Убираем кнопки, редактируя предыдущее сообщение
        await query.edit_message_reply_markup(reply_markup=None)
        target_chat = query.message.chat_id
    else:
        target_chat = update.effective_chat.id

    # Инициализация данных пользователя
    context.user_data["check_in"] = None
    context.user_data["check_out"] = None

    # Отправляем новое сообщение с календарём
    await context.bot.send_message(
        chat_id=target_chat,
        text="📅 Выберите дату заезда",
        reply_markup=build_calendar(date.today().year, date.today().month)
    )

    return SELECTING_CHECKIN


async def calendar_callback(update: Update, context: CallbackContext):
    """Обработка нажатий календаря"""
    query = update.callback_query
    await query.answer()
    data = query.data

    check_in = context.user_data.get("check_in")
    check_out = context.user_data.get("check_out")

    # Навигация по месяцам
    if data.startswith(CB_NAV):
        _, y, m = data.split(":")
        y, m = int(y), int(m)
        await query.edit_message_reply_markup(
            reply_markup=build_calendar(y, m, check_in, check_out)
        )
        return SELECTING_CHECKIN if not check_in else SELECTING_CHECKOUT

    # Выбор даты
    if data.startswith(CB_SELECT):
        today = date.today()

        try:
            _, d = data.split(":")
            selected_date = date.fromisoformat(d)
        except Exception as e:
            print(f"[ERROR] Некорректная дата из callback: {data}, {e}")
            await query.answer("⚠️ Ошибка выбора даты. Попробуйте снова", show_alert=True)
            await update.message.reply_text("Ошибка при выборе даты.")
            return SELECTING_CHECKIN

        # ✅ Проверяем, выбрал ли пользователь check-in
        if check_in is None:
            # 🚫 Нельзя выбрать дату заезда в прошлом
            if selected_date <= today:
                await query.answer("🚫 Бронирование начиная с завтра", show_alert=True)
                return SELECTING_CHECKIN

            # ✅ Сохраняем дату заезда
            context.user_data["check_in"] = selected_date
            await query.edit_message_text(
                f"✅ Дата заезда: {selected_date}\nТеперь выберите дату выезда"
            )
            await query.edit_message_text(
                f"✅ Дата заезда: {selected_date}\nТеперь выберите дату выезда",
                reply_markup=build_calendar(selected_date.year, selected_date.month, check_in=selected_date)
            )
            return SELECTING_CHECKOUT
        # Если уже выбрали check-in, проверяем check-out
        if selected_date <= check_in:
            await query.answer("⛔ Дата выезда должна быть позже заезда", show_alert=True)
            return SELECTING_CHECKOUT

        context.user_data["check_out"] = selected_date

        async with get_async_session() as session:
            result = await session.execute(ApartmentType.__table__.select())
            types = [{"id": t.id, "name": t.name} for t in result.fetchall()]
        # Сохраняем в user_data
        context.user_data["types"] = types
        context.user_data["selected_types"] = []

        # Строим клавиатуру
        keyboard = build_types_keyboard(types, [])
        reply_markup = InlineKeyboardMarkup(keyboard)

        

        await query.edit_message_text(f"✅ Ищем с: {check_in} по {selected_date}\n"
                            "Выберите тип. Можно выбрать несколько выриантов:",
                            reply_markup=reply_markup)
        
        return APTS_TYPES_SELECTION


async def handle_apartment_type_multiselection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия при мультивыборе типов квартиры."""
    query = update.callback_query
    await query.answer()

    data = query.data
    selected = context.user_data.get("selected_types", [])

    # 🔹 1. Пользователь нажал подтверждение
    if data == "confirm_types":
        if not selected:
            # ❌ Ошибка — выбор пустой
            await query.message.reply_text(
                text="⚠️ Вы не выбрали ни одного типа. Пожалуйста, выберите хотя бы один.",
                reply_markup=InlineKeyboardMarkup(build_types_keyboard(context.user_data["types"], selected))
            )
            return APTS_TYPES_SELECTION
        
        # ✅ Выбор подтверждён
        selected_names = [t["name"] for t in context.user_data["types"] if t["id"] in selected]
        keyboard = build_price_filter_keyboard()
        await query.edit_message_text(
            text="✅ Вы выбрали типы: " + ", ".join(selected_names) + "\n💰 Выберите ценовой интервал:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        context.user_data["selected_names"] = selected_names

        # ⬇️ Здесь вызываем следующий шаг
        return PRICE_FILTER_SELECTION   

    # 🔹 2. Пользователь выбрал/снял галочку с типа
    try:
        type_id = int(data.replace("type_", ""))
    except ValueError:
        await query.edit_message_text("Ошибка выбора. Попробуйте снова.")
        return APTS_TYPES_SELECTION

    if type_id in selected:
        selected.remove(type_id)
    else:
        selected.append(type_id)

    context.user_data["selected_types"] = selected
    print(f"TRY_SELECTED: {selected}")
    # Перерисовываем клавиатуру
    keyboard = build_types_keyboard(context.user_data["types"], selected)
    await query.edit_message_text(
        text="✅ Выберите тип(ы) квартиры:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return APTS_TYPES_SELECTION

async def handle_price_filter_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора ценового диапазона пользователем."""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Определяем выбранный диапазон
    if data == "price_all":
        context.user_data["price_filter"] = None
        price_text = "Без фильра по цене"
    elif data == "price_0_3000":
        context.user_data["price_filter"] = {"min": 0, "max": 2999}
        price_text = "0 – 3000 ₽"
    elif data == "price_3000_5900":
        context.user_data["price_filter"] = {"min": 3000, "max": 5999}
        price_text = "3000 – 5900 ₽"
    elif data == "price_6000_plus":
        context.user_data["price_filter"] = {"min": 6000, "max": None}
        price_text = "6000+ ₽"
    elif data.startswith("apt_"):#callback реагирует на нажатие кнопок навигации в full_view_booking
        await show_filtered_apartments_navigation(update, context)
        return
    elif data.startswith("book_"): #коллбэк реагирует на нажатие кнопки Забронировать в full_view_booking
        apartment_id = int(data.split("_")[1])
        price = float(data.split("_")[2])
        context.user_data["chosen_apartment"] = apartment_id
        context.user_data["actual_price"] = price
        await handle_guests_number(update, context)
        return GUESTS_NUMBER
    elif data == "start_search":
        # Сброс всех пользовательских данных, связанных с поиском
        for key in ["check_in", "check_out", "price_filter", "chosen_apartment", "actual_price", "apartment_type"]:
            context.user_data.pop(key, None)

        await start_search(update, context)
        return SELECTING_CHECKIN 
    else:
        await query.message.reply_text("Ошибка выбора, попробуйте снова.")
        return PRICE_FILTER_SELECTION
    
    check_in = context.user_data.get("check_in")
    check_out = context.user_data.get("check_out")
    selected_names = context.user_data.get("selected_names")
    context.user_data["price_text"] = price_text

    # ✅ Демонстрируем пользователю его выбор
    await query.edit_message_text(
        f"✅ Вы выбрали аренду с: {check_in} по {check_out}\n"
        f"✅ Вы выбрали типы: {', '.join(selected_names)}\n"
        f"✅ Вы выбрали фильтр по цене: {price_text}\n\n"
        "🔍 Переходим к подбору квартир..."
    )

    # 1️⃣ Фильтрация квартир
    apartment_ids = await filter_apartments(update, context)

    if not apartment_ids:
        return ConversationHandler.END

    # 2️⃣ Сразу переходим к показу первой карточки
    await show_filtered_apartments(update, context)   #вызов функции показа карточек


# === Вспомогательная функция ===

async def send_message(update: Update, text: str,reply_markup=None):
    """Универсальная отправка сообщения (поддержка Message и CallbackQuery)."""
    if update.message:
        await update.message.reply_text(text,reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text,reply_markup = reply_markup)


async def filter_apartments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Фильтрация квартир и сохранение результатов в user_data."""
    user_id = context.user_data.get("user_id")
    session_id = context.user_data.get("session_id")
    type_ids = context.user_data.get("selected_types")
    check_in = context.user_data.get("check_in",date)
    check_out = context.user_data.get("check_out",date)
    price = context.user_data.get("price_filter")

    filters = {
        "type_ids": type_ids,
        "check_in": check_in.isoformat() if hasattr(check_in, "isoformat") else check_in,
        "check_out": check_out.isoformat() if hasattr(check_out, "isoformat") else check_out,
        "price": price
    }
    print(f"DEBUG_DATE_TYPE: {type(check_in)}")
    if not user_id:
        await send_message(update, "Ошибка: не найден user_id. Пожалуйста, начните сначала /start")
        return None, None

    # ✅ Получаем список квартир
    apartment_ids, apartments, new_search = await get_apartments(check_in, check_out, session_id, user_id, filters)

    if not apartment_ids:
        keyboard = [
        [InlineKeyboardButton("🔍 Новый поиск", callback_data="start_search")]
    ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await send_message(update, "❌ По выбранным параметрам ничего не найдено.\nПопробуйте изменить фильтры или выбрать другие даты",reply_markup=reply_markup)

        return ConversationHandler.END

    # ✅ Сохраняем результаты в контексте
    context.user_data.update({
            "filtered_apartments_ids": apartment_ids,
            "filtered_apartments": apartments,
            "new_search_id": new_search.id
        })


    # ✅ Сообщаем пользователю, сколько найдено объектов
    await send_message(update, f"🔍 Найдено предложений: {len(apartment_ids)}")
    return apartment_ids


async def show_filtered_apartments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    """
    Отображает карточку квартиры (первая или при навигации).
    Если индекс не передан в callback_data → показывается первая карточка.
    показывает всю галлерею. Подключается в двух местах
    """
    query = update.callback_query
    data = query.data if query else None

    # ✅ список квартир
    apts = context.user_data.get("filtered_apartments", [])
    if not apts:
        if query:
            await query.edit_message_text("❌ Список квартир пуст.")
        else:
            await update.message.reply_text("❌ Список квартир пуст.")
        return ConversationHandler.END

    # ✅ определяем индекс (по кнопке или дефолт = 0)
    current_index = 0
    if data and (data.startswith("apt_next_") or data.startswith("apt_prev_")):
        try:
            current_index = int(data.split("_")[-1])
        except (ValueError, IndexError):
            await query.message.reply_text("Ошибка индекса. Попробуйте снова.")
            return ConversationHandler.END

    # ✅ ограничиваем индекс допустимым диапазоном
    total = len(apts)
    if current_index < 0:
        current_index = 0
    if current_index >= total:
        current_index = total - 1

    current_apartment = apts[current_index]

    # ✅ формируем карточку
    text, media, markup = booking_apartment_card_full(current_apartment, current_index, total=total)

    # ✅ объект для ответа
    msg_target = query.message if query else update.message

    # ✅ удаляем старое сообщение, если нужно
    if query:
        await msg_target.delete()

    # ✅ отправляем фото/текст
    if media and len(media) > 1:
        await msg_target.reply_media_group(media)
        await msg_target.reply_text(text, reply_markup=markup, parse_mode="HTML")
    elif media and len(media) == 1:
        await msg_target.reply_photo(media[0].media, caption=text, reply_markup=markup, parse_mode="HTML")
    else:
        await msg_target.reply_text(text, reply_markup=markup, parse_mode="HTML")


async def handle_guests_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ✅ первый вызов - нажата кнопка
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text("Введите количество гостей:")
        return GUESTS_NUMBER

    # ✅ второй вызов - пользователь отправил число
    elif update.message:
        try:
            guests_number = int(update.message.text)
            if guests_number <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Введите корректное число (>0):")
            return GUESTS_NUMBER

        context.user_data["guest_count"] = guests_number
        
        # Запрашиваем комментарий
        keyboard = [[KeyboardButton("направить комментарий")]]
        await update.message.reply_text(
            "🕊 Вы можете направить собственнику доп.информацию:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        return BOOKING_COMMENT


async def handle_bookings_notion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text.strip()
    if not comment or comment.lower() == "направить комментарий":
        comment = "Других подробностей нет"
    else:
        comment = sanitize_message(comment)[:255]
    print(f"[DEBUG] context.user_data: {context.user_data}")
    check_in = context.user_data.get("check_in") 
    check_out = context.user_data.get("check_out")
    price = context.user_data.get("actual_price")
    total = (check_out - check_in).days * price

    async with get_async_session() as session:
        booking = Booking(
            user_id = context.user_data['user_id'],
            apartment_id = context.user_data['chosen_apartment'],
            status_id = 5,
            guest_count = context.user_data['guest_count'],
            total_price = total,
            comments = comment,
            check_in = check_in,
            check_out = check_out
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)

        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.apartment)
                .selectinload(Apartment.apartment_type),
                selectinload(Booking.apartment)
                .selectinload(Apartment.images),
                selectinload(Booking.apartment)
                .selectinload(Apartment.owner) 
            )
            .where(Booking.id == booking.id)
        )
        result = await session.execute(stmt)
        booking_full = result.scalar_one()
        print(f"[DEBUG] Отправка запроса владельцу для booking_id={booking_full.id}")
        await send_booking_request_to_owner(context.bot,booking_full)
        print(f"[DEBUG] Сообщение владельцу должно быть отправлено")

        await update.message.reply_text("✅ Ваше бронирование создано. После подтверждения заявки владельцем бот с вами свяжется.")
        text, media = show_booked_appartment(booking_full)

    
        if media:
            await update.message.reply_media_group(media)
            await update.message.reply_text(text, parse_mode="HTML")
        await session.commit()

    return ConversationHandler.END



async def show_filtered_apartments_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показ карточки квартиры в одном сообщении (поддержка навигации кнопками).
    Используется только первое фото.
    Сейчас эта функия задействована после нажатия на кнопки навигации
    """
    query = update.callback_query
    data = query.data if query else None

    apts = context.user_data.get("filtered_apartments", [])
    if not apts:
        await (query.message.edit_text("❌ Список квартир пуст.") if query else update.message.reply_text("❌ Список квартир пуст."))
        return ConversationHandler.END

    new_search_id = context.user_data.get("new_search_id")

    # Определяем индекс
    current_index = 0
    if data and (data.startswith("apt_next_") or data.startswith("apt_prev_")):
        try:
            current_index = int(data.split("_")[-1])
        except (ValueError, IndexError):
            await query.message.reply_text("Ошибка индекса. Попробуйте снова.")
            return ConversationHandler.END
    

    # Ограничение диапазона
    total = len(apts)
    current_index = max(0, min(current_index, total - 1))

    async with get_async_session() as session:
        await session.execute(
            sa_update(SearchSession)
            .where(SearchSession.id == new_search_id)
            .values(current_index=current_index)
        )
        await session.commit()

    apartment = apts[current_index]
    text, media, markup = booking_apartment_card_full(apartment, current_index, total)

    # ✅ используем только первое фото
    photo = media[0].media if media else None

    # 🔥 Если callback → редактируем старое сообщение
    if query:
        if photo:
            await query.message.edit_media(
                media=InputMediaPhoto(photo, caption=text, parse_mode="HTML"),
                reply_markup=markup
            )
        else:
            await query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        return

    # 🔥 Если первый показ → отправляем новое сообщение
    if photo:
        await update.message.reply_photo(photo, caption=text, reply_markup=markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")


# === Отмена ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена поиска"""
    context.user_data.clear()
    await update.message.reply_text("❌ Поиск отменён",reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END
