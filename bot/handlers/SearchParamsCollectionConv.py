import datetime
from datetime import date
from enum import IntEnum

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
from geoalchemy2.shape import to_shape

from decimal import Decimal
from db.db_async import get_async_session

from utils.keyboard_builder import build_types_keyboard, build_price_filter_keyboard, build_calendar, CB_NAV, CB_SELECT
from utils.apts_search_session import get_apartments
from utils.booking_navigation_view import booking_apartment_card_full
from utils.booking_complit_view import show_booked_appartment
from utils.escape import safe_html
from utils.request_confirmation import send_booking_request_to_owner
from utils.message_tricks import cleanup_messages, add_message_to_cleanup, send_message, sanitize_message

from db.models import (ApartmentType,
                       Apartment,
                       Session,
                       SearchSession,
                       Booking,
                       BookingType)

from utils.logging_config import structured_logger, log_db_select

from sqlalchemy import update as sa_update, select 
from sqlalchemy.orm import selectinload

import json
from telegram.error import TelegramError

def safe_json(obj):
    """Безопасное преобразование для логов, даже если там non-serializable"""
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return str(obj)



# Состояния диалога
(SELECTING_CHECKIN, 
 SELECTING_CHECKOUT, 
 SELECTING_TYPES, 
 SELECTING_PRICE,
 VIEWING_APARTMENTS,
 ENTERING_GUESTS,
 BOOKING_COMMENT)= range(7)


class BookingStatus(IntEnum):
    BOOKING_STATUS_PENDING = 5
    BOOKING_STATUS_CONFIRMED = 6

PRICE_MAP = {
    "price_all":        (None, {"text": "Без фильтра по цене"}),
    "price_0_3000":     ({"min": 0,    "max": 2999}, {"text": "0 – 3000 ₽"}),
    "price_3000_5900":  ({"min": 3000, "max": 5999}, {"text": "3000 – 5900 ₽"}),
    "price_6000_plus":  ({"min": 6000, "max": None}, {"text": "6000+ ₽"}),
}

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт поиска жилья: инициализация данных пользователя"""
    # Определяем источник вызова
    try:
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            # Убираем кнопки, редактируя предыдущее сообщение
            await query.message.delete()
            target_chat = query.message.chat_id
        else:
            target_chat = update.effective_chat.id

        # Инициализация данных пользователя
        context.user_data["check_in"] = None
        context.user_data["check_out"] = None
        context.user_data["price_filter"] = None
        context.user_data["chosen_apartment"] = None
        context.user_data["actual_price"] = None
        context.user_data["apartment_type"] = None
        context.user_data["filtered_apartments_ids"] = None
        context.user_data["filtered_apartments"] = None
        context.user_data["new_search_id"] = None
        
        await cleanup_messages(context)
        
        structured_logger.info(
            "Initiate start_search command",
            user_id = target_chat,
            action = "Start new search"
        )

        # Отправляем новое сообщение с календарём
        msg = await context.bot.send_message(
            chat_id=target_chat,
            text="📅 Выберите дату заезда",
            reply_markup=build_calendar(date.today().year, date.today().month)
        )
        await add_message_to_cleanup(context,msg.chat_id,msg.message_id)
        return SELECTING_CHECKIN
    
    except Exception as e:

        structured_logger.error(
            f"Critical error in start new search: {str(e)}",
            user_id=target_chat,
            action="Start new object",
            exception=e,
            context={
                'tg_user_id': target_chat,
                'error_type': type(e).__name__
            }
        )
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте позже или обратитесь в поддержку."
        )
    return ConversationHandler.END

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
        msg = await query.edit_message_reply_markup(
            reply_markup=build_calendar(y, m, check_in, check_out)
        )
        await add_message_to_cleanup(context,msg.chat_id,msg.message_id)
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

            return SELECTING_CHECKIN

        # ✅ Проверяем, выбрал ли пользователь check-in
        if check_in is None:
            # 🚫 Нельзя выбрать дату заезда в прошлом
            if selected_date <= today:
                await query.answer("🚫 Бронирование начиная с завтра", show_alert=True)
                return SELECTING_CHECKIN

            # ✅ Сохраняем дату заезда
            context.user_data["check_in"] = selected_date

            msg = await query.edit_message_text(
                f"✅ Дата заезда: {selected_date}\nТеперь выберите дату выезда",
                reply_markup=build_calendar(selected_date.year, selected_date.month, check_in=selected_date)
            )
            await add_message_to_cleanup(context,msg.chat_id,msg.message_id)
            return SELECTING_CHECKOUT
        # Если уже выбрали check-in, проверяем check-out
        if selected_date <= check_in:
            await query.answer("⛔ Дата выезда должна быть позже заезда", show_alert=True)
            return SELECTING_CHECKOUT

        context.user_data["check_out"] = selected_date

        async with get_async_session() as session:
            result = await session.execute(select(ApartmentType).order_by(ApartmentType.id))
            types = [{"id": t.id, "name": t.name} for t in result.scalars().all()]
        # Сохраняем в user_data
        context.user_data["types"] = types
        context.user_data["selected_types"] = []

        # Строим клавиатуру
        keyboard = build_types_keyboard(types, [])
        reply_markup = InlineKeyboardMarkup(keyboard)

        

        msg = await query.edit_message_text(
                f"🔦 Поиск по датам:\n"
                f"с <b>{check_in}</b> по <b>{selected_date}</b>\n"
                "Выберите тип. Можно выбрать несколько вариантов:",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        await add_message_to_cleanup(context,msg.chat_id,msg.message_id)
        return SELECTING_TYPES


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
            return SELECTING_TYPES
        
        # ✅ Выбор подтверждён
        selected_names = [t["name"] for t in context.user_data["types"] if t["id"] in selected]
        keyboard = build_price_filter_keyboard()
        await query.edit_message_text(
            text="✅ Вы выбрали типы: " + ", ".join(selected_names) + "\n💰 Выберите ценовой интервал:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        context.user_data["selected_names"] = selected_names

        # ⬇️ Здесь вызываем следующий шаг
        return SELECTING_PRICE   

    # 🔹 2. Пользователь выбрал/снял галочку с типа
    try:
        type_id = int(data.replace("type_", ""))
    except ValueError:
        await query.edit_message_text("Ошибка выбора. Попробуйте снова.")
        return SELECTING_TYPES

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
    return SELECTING_TYPES

async def handle_price_filter_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    price_range, meta = PRICE_MAP.get(data, (None, None))
    if meta is None:
        structured_logger.warning("Unknown price filter callback_data: %s", data)
        await query.answer("Неизвестный фильтр цены.", show_alert=True)
        return

    context.user_data["price_filter"] = price_range
    context.user_data["price_text"] = meta["text"]
    
    check_in = context.user_data.get("check_in")
    check_out = context.user_data.get("check_out")
    selected_names = context.user_data.get("selected_names")

    # ✅ Демонстрируем пользователю его выбор
    await query.edit_message_text(
        f"✅ Вы выбрали аренду с: {check_in} по {check_out}\n"
        f"✅ Вы выбрали типы: {', '.join(selected_names)}\n"
        f"✅ Вы выбрали фильтр по цене: {meta["text"]}\n\n"
        "🔍 Переходим к подбору квартир..."
    )

    # Filter apartments
    try:
        apartment_ids = await filter_apartments(update, context)
        print(f"DEBUG apartment_ids={apartment_ids}, type={type(apartment_ids)}")
        if not apartment_ids:
            return ConversationHandler.END
        
        # ✅ Show count BEFORE the card
        count_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🔍 Найдено предложений: {len(apartment_ids)}"
        )
        await add_message_to_cleanup(context, count_msg.chat_id, count_msg.message_id)
        
        structured_logger.info(
            "Search filter created",
            action = "search filters implemented",
            context = {
                'in': check_in.isoformat() if check_in else None,
                'out': check_out.isoformat() if check_out else None,
                'price_range':price_range,
                'types': selected_names,
                'number_candidates': len(apartment_ids) 
            }
        )

        # Now show the first apartment
        await show_apartment_card(update, context, index=0)
        return VIEWING_APARTMENTS
        
    except Exception as e:
        structured_logger.error(f"Error filtering apartments: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Произошла ошибка. Попробуйте снова /start_search"
        )
        return ConversationHandler.END

async def show_apartment_card(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int = 0, is_navigation: bool = False):
    """Unified function to display apartment cards."""
    apts = context.user_data.get("filtered_apartments", [])
    if not apts:
        await send_message(update, "❌ Список квартир пуст")
        return ConversationHandler.END
    
    total = len(apts)
    index = max(0, min(index, total - 1))
    
    apartment = apts[index]
    text, media, markup = booking_apartment_card_full(apartment, index, total)
    
    query = update.callback_query
    
    # Update search session index
    if "new_search_id" in context.user_data:
        async with get_async_session() as session:
            await session.execute(
                sa_update(SearchSession)
                .where(SearchSession.id == context.user_data["new_search_id"])
                .values(current_index=index)
            )
            await session.commit()
    """  
    # Display apartment
    if query and is_navigation:
        # ✅ Edit existing message (only during navigation)
        photo = media[0].media if media else None
        if photo:
            await query.message.edit_media(
                media=InputMediaPhoto(photo, caption=text, parse_mode="HTML"),
                reply_markup=markup
            )
        else:
            await query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        # ✅ Send new message (first display or non-query updates)
        chat_id = update.effective_chat.id
        
        if media and len(media) > 1:
            await context.bot.send_media_group(chat_id=chat_id, media=media)
            sent = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode="HTML")
        elif media and len(media) == 1:
            sent = await context.bot.send_photo(chat_id=chat_id, photo=media[0].media, caption=text, reply_markup=markup, parse_mode="HTML")
        else:
            sent = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode="HTML")
        
        await add_message_to_cleanup(context, sent.chat_id, sent.message_id)
    """
    # Display apartment
    try:
        if query and is_navigation:
            structured_logger.debug(
                "Editing apartment view",
                context={
                    "mode": "edit_media" if (media and media[0].media) else "edit_text",
                    "photo": safe_json(media[0].media if media else None),
                    "caption/text": text,
                    "reply_markup": safe_json(markup.to_dict() if markup else None),
                }
            )

            photo = media[0].media if media else None

            if photo:
                await query.message.edit_media(
                    media=InputMediaPhoto(
                        media=photo,
                        caption=text,
                        parse_mode="HTML"
                    ),
                    reply_markup=markup
                )
            else:
                # Отправка нового сообщения
                await cleanup_messages(context)
                sent = await send_message(update, text, reply_markup=markup,parse_mode="HTML")
                await add_message_to_cleanup(context, sent.chat_id, sent.message_id)

        else:
            chat_id = update.effective_chat.id

            structured_logger.debug(
                "Sending apartment view",
                context={
                    "mode": (
                        "media_group" if (media and len(media) > 1)
                        else "photo" if (media and len(media) == 1)
                        else "text"
                    ),
                    "media_list": safe_json([m.media for m in media] if media else None),
                    "caption/text": text,
                    "reply_markup": safe_json(markup.to_dict() if markup else None),
                }
            )

            if media and len(media) > 1:
                await context.bot.send_media_group(chat_id=chat_id, media=media)
                sent = await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )

            elif media and len(media) == 1:
                sent = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=media[0].media,
                    caption=text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )

            else:
                sent = await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )

            await add_message_to_cleanup(context, sent.chat_id, sent.message_id)

    except TelegramError as e:
        structured_logger.error(
            "Telegram API error while sending apartment",
            context={
                "error": str(e),
                "media_list": safe_json([m.media for m in media] if media else None),
                "text": text,
                "reply_markup": safe_json(markup.to_dict() if markup else None),
                "is_navigation": is_navigation,
            }
        )
        raise

    except Exception as e:
        structured_logger.error(
            "Unexpected error while sending apartment",
            context={
                "error": str(e),
                "media_list": safe_json([m.media for m in media] if media else None),
                "text": text,
                "reply_markup": safe_json(markup.to_dict() if markup else None),
                "is_navigation": is_navigation,
            }
        )
        raise

async def navigate_apartments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle prev/next navigation."""
    query = update.callback_query
    await query.answer()
    
    try:
        index = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        await query.answer("❌ Ошибка навигации", show_alert=True)
        return VIEWING_APARTMENTS
    
    await show_apartment_card(update, context, index,is_navigation=True)
    return VIEWING_APARTMENTS

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _,apartment_id,price = query.data.split('_')               
        await query.edit_message_reply_markup(reply_markup=None)
    except ValueError:
        await query.edit_message_text("Ошибка. Начните поиск заново.")
        structured_logger.warning("Не удалось убрать клавиатуру: %s", e)
        return ConversationHandler.END

    
    apartment_id = int(apartment_id)
    price = Decimal(price) 
    
    context.user_data["chosen_apartment"] = apartment_id
    context.user_data["actual_price"] = price

    await query.message.reply_text("Введите количество гостей:")
    return ENTERING_GUESTS

async def handle_entering_guest_number(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        ENTERING_GUESTS = int(update.message.text)
        if ENTERING_GUESTS <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите корректное число (>0):")
        return ENTERING_GUESTS

    context.user_data["guest_count"] = ENTERING_GUESTS
    
    # Запрашиваем комментарий
    keyboard = [[KeyboardButton("направить комментарий")]]
    await update.message.reply_text(
        "🕊 Вы можете направить собственнику доп.информацию:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return BOOKING_COMMENT

async def finalize_booking (update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        comment = update.message.text.strip()
        if not comment or comment.lower() == "направить комментарий":
            comment = "Комментариев нет"
        else:
            comment = sanitize_message(comment)[:255]
        print(f"[DEBUG] context.user_data: {context.user_data}")
        check_in = context.user_data.get("check_in") 
        check_out = context.user_data.get("check_out")
        price = context.user_data.get("actual_price")
        total = (check_out - check_in).days * price
        msg_id = context.user_data.get("last_filter_apartment_message_id")
        cht_id = context.user_data.get("last_filter_apartment_chat_id")

        async with get_async_session() as session:
            session_id = context.user_data.get("session_id")
            if not session_id:
                # создаём новую сессию
                new_session = Session(tg_user_id=context.user_data['tg_user_id'], role_id = 1,last_action={"event": "order_started"})
                session.add(new_session)
                await session.flush()  # получаем id новой сессии
                session_id = new_session.id
                context.user_data["session_id"] = session_id  # кладём обратно в контекст

            booking = Booking(
                tg_user_id = context.user_data['tg_user_id'],
                apartment_id = context.user_data['chosen_apartment'],
                status_id = BookingStatus.BOOKING_STATUS_PENDING,
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

            structured_logger.info (
                "New order request created",
                user_id = Booking.tg_user_id,
                action = "New booking request",
                context={
                    'booking_id':Booking.id,
                    'Address': Booking.apartment.short_address,
                    'Price': Booking.total_price,
                    'in': Booking.check_in.isoformat() if Booking.check_in else None,
                    'out': Booking.check_out.isoformat() if Booking.check_out else None
                
                }
            )
        
            msg_ids = []

            if media:
                media_messages = await update.message.reply_media_group(media)
                msg_ids.extend([m.message_id for m in media_messages])

            msg_text = await update.message.reply_text(text, parse_mode="HTML")
            msg_ids.append(msg_text.message_id)

            # Сохраняем список ID в session.last_action
            session_obj = await session.get(Session, session_id)
            if session_obj:
                session_obj.last_action = {
                    "event": "booking_created_message",
                    "message_ids": msg_ids
                }
                    
            await session.commit()

            if cht_id and msg_id:
                try:
                    await context.bot.delete_message(chat_id=cht_id, message_id=msg_id)
                    print(f"[DEBUG] Удалено сообщение с карточкой (msg_id={msg_id})")
                except Exception as e:
                    print(f"[WARNING] Не удалось удалить сообщение с карточкой: {e}")

            context.user_data["last_filter_apartment_message_id"] = None
            context.user_data["last_filter_apartment_chat_id"] = None

    except Exception as e:

        structured_logger.error(
            f"Critical error in new booking creation: {str(e)}",
            action="Create new booking",
            exception=e,
            context={

                'error_type': type(e).__name__
            }
        )
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте позже или обратитесь в поддержку."
        )


    return ConversationHandler.END

# === Вспомогательная функция ===
async def filter_apartments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Фильтрация квартир и сохранение результатов в user_data."""
    tg_user_id = context.user_data.get("tg_user_id")
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
    if not tg_user_id:
        await send_message(update, "Ошибка: не найден user_id. Пожалуйста, начните сначала /start")
        return None

    # ✅ Получаем список квартир
    apartment_ids, apartments, new_search = await get_apartments(check_in, check_out, session_id, tg_user_id, filters)

    if not apartment_ids:
        keyboard = [
        [InlineKeyboardButton("🔍 Новый поиск", callback_data="start_search")]
    ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await send_message(update, "❌ По выбранным параметрам ничего не найдено.\nПопробуйте изменить фильтры или выбрать другие даты",reply_markup=reply_markup)

        return []

    # ✅ Сохраняем результаты в контексте
    context.user_data.update({
            "filtered_apartments_ids": apartment_ids,
            "filtered_apartments": apartments,
            "new_search_id": new_search.id
        })

    return apartment_ids

async def handle_show_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    apt_id = int(query.data.split("_")[-1])

    async with get_async_session() as session:
        apartment = (
            await session.execute(select(Apartment).where(Apartment.id == apt_id))
        ).scalar_one_or_none()

        if not apartment or not apartment.coordinates:
            await query.message.reply_text("⚠️ Ошибка карты: координаты отсутствуют.")
            return VIEWING_APARTMENTS

        # Преобразуем в координаты
        point = to_shape(apartment.coordinates)
        lat, lon = point.y, point.x

        # Проверяем, показывалась ли уже карта
        previous_msg_id = context.user_data.get("map_message_id")
        print(f"DEBUG_previous_MAP: {previous_msg_id}")
        if previous_msg_id:
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=previous_msg_id)
            except Exception:
                pass

        msg = await query.message.reply_location(latitude=lat, longitude=lon)
        context.user_data["map_message_id"] = msg.message_id

        return VIEWING_APARTMENTS
    
# === Отмена ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена поиска"""
    await cleanup_messages(context)
    context.user_data.clear()
    await update.message.reply_text("❌ Поиск отменён",reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END
