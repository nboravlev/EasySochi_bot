from telegram import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    Update, 
    ReplyKeyboardRemove, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
    )
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackQueryHandler
)

from sqlalchemy import update as sa_update, select 
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from datetime import datetime
import logging
from sqlalchemy.orm import selectinload

from db.db_async import get_async_session

from db.models.users import User
from db.models.sessions import Session
from db.models.roles import Role
from db.models.search_sessions import SearchSession
from db.models.apartments import Apartment
from db.models.bookings import Booking
from db.models.booking_chat import BookingChat

from utils.user_session import register_user_and_session
from utils.owner_objects_request_from_menu import prepare_owner_objects_cards
from utils.renter_bookings_request_from_menu import prepare_renter_bookings_cards
from utils.owner_orders_request_from_menu import prepare_owner_orders_cards

from utils.logging_config import log_function_call, LogExecutionTime, get_logger

from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

# === Состояния ===
(CHOOSING_ROLE, 
 ASK_PHONE, 
 ASK_LOCATION,
 VIEW_BOOKINGS,
 VIEW_OBJECTS,
 VIEW_ORDERS
)= range(6)

# === Роли ===
ROLE_MAP = {
    "🏠 арендовать жильё": 1,  # tenant
    "🏘 сдавать жильё": 2     # owner
}

# === Дополнительные действия ===
EXTRA_ACTIONS = {
    "📑 мои бронирования": VIEW_BOOKINGS,
    "🏢 мои объекты": VIEW_OBJECTS
}

WELCOME_TEXT = (
"Здравствуйте, \n Я Николай Боравлев, программист и спортсмен из Сочи. Автоматизирую процессы с 2023 г.\n\n"
"EasySochi это мой продукт для сдачи в аренду и поиску недвижимости в Сочи, коммуникации пользователей и управления своими бронированиями и квартирами.\n"
"Моя цель - создать альтернативу дорогим агрегаторам, и за счет минимальной комиссии за пользование инструментом предложить пользователям конкурентную цену.\n"
"В широком смысле, это настраиваемый масштабируемый продукт для управления бизнесом в сфере услуг, аренды, проката и т.п. По вопросам разработки и внедрения для Вашего бизнеса напишите мне в раздел Помощь"

)

WELCOME_PHOTO_URL = "AgACAgIAAxkBAAInXWiZ1L3ZKAPDkD46a2eTg3lETNBQAALY-TEb3UDQSMUUqvPV6sH4AQADAgADeQADNgQ"  # белый
#  AgACAgIAAxkBAAInX2iZ1QTPjfWJ1lPRX4yRoA9m4GwkAALc-TEb3UDQSPIh4FWDh0vUAQADAgADeQADNgQ -темный
#  AgACAgIAAxkBAAInYWiZ1SknQvl_1rUvLlzty-hAHMMsAALe-TEb3UDQSBOatzVIlUKsAQADAgADeQADNgQ - с Лерой
# AgACAgIAAxkBAAInXWiZ1L3ZKAPDkD46a2eTg3lETNBQAALY-TEb3UDQSMUUqvPV6sH4AQADAgADeQADNgQ - белый
# Функция для группировки кнопок по N в ряд
def chunk_buttons(buttons, n=2):
    return [buttons[i:i+n] for i in range(0, len(buttons), n)]
# === Старт ===
@log_function_call(action="user_start_command")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get logger with user context
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger = get_logger(__name__, user_id=user_id, chat_id=chat_id)
    try:
        with LogExecutionTime("user_registration", logger, user_id, chat_id):
            if update.message:
                user_choice = update.message.text
            elif update.callback_query:
                user_choice = update.callback_query.data
            else:
                logger.warning("choose_role: ни message, ни callback_query нет в update")
                return ConversationHandler.END
            
            # Enhanced logging with context
            logger.info(
                f"User started bot and chose role: {user_choice}",
                extra={
                    'action': 'role_selection',
                    'user_choice': user_choice,
                    'user_id': user_id,
                    'chat_id': chat_id
                }
            )
        # Формируем список всех кнопок
        all_buttons = list(ROLE_MAP.keys()) + list(EXTRA_ACTIONS.keys())
        
        # Группируем по две в ряд
        keyboard = chunk_buttons(all_buttons, n=2)
        
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True
        )

        if update.message:
            await update.message.reply_photo(
                photo=WELCOME_PHOTO_URL,  # Можно file_id или путь к файлу
                caption=WELCOME_TEXT,
                reply_markup=reply_markup
            )
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_photo(
                photo=WELCOME_PHOTO_URL,
                caption=WELCOME_TEXT,
                reply_markup=reply_markup
            )

        return CHOOSING_ROLE
    except Exception as e:
        logger.error(
        f"Error in start handler: {str(e)}",
        extra={
            'action': 'start_error',
            'user_id': user_id,
            'chat_id': chat_id,
            'error_type': type(e).__name__
        },
        exc_info=True
        )
        return ConversationHandler.END

# === Выбор роли и регистрация ===
async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get logger with user context
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger = get_logger(__name__, user_id=user_id, chat_id=chat_id)
    try:
        user_choice = update.message.text
        if user_choice in EXTRA_ACTIONS:
            next_state = EXTRA_ACTIONS[user_choice]
            if next_state == VIEW_BOOKINGS:
                await select_renter_bookings(update, context)
                return VIEW_BOOKINGS
            elif next_state == VIEW_OBJECTS:
                await select_owner_objects(update, context)
                return VIEW_OBJECTS
        
        if user_choice in ROLE_MAP:
            role_id = ROLE_MAP[user_choice]
            tg_user = update.effective_user
            bot_id = context.bot.id
            logger.info(f"User {tg_user.id} chose role: {role_id}")

            user, session, is_new_user = await register_user_and_session(tg_user, bot_id, role_id)      
        
        

        # ✅ Регистрируем пользователя и создаём сессию

            context.user_data.update({
                "user_id": user.id,
                "session_id": session.id,
                "role_id": role_id,
                "is_new_user": is_new_user,
                "tg_user_id": tg_user.id
            })

            if not user.phone_number:
                await update.message.reply_text(
                    "Спасибо! Вы выбрали роль.",
                    reply_markup=ReplyKeyboardRemove()
                )
                keyboard = [
                    [KeyboardButton("📞 Нажмите здесь, чтобы отправить", request_contact=True)], 
                    ["Пропустить"]
                ]
                await update.message.reply_text(
                    "Пожалуйста, отправьте ваш номер телефона (или нажмите 'Пропустить'):",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                )

                return ASK_PHONE
            else:
                await update.message.reply_text(
                    "Ваш номер уже есть в базе.",
                    reply_markup=ReplyKeyboardRemove()
                )

                return await _ask_for_location(update)
            
        await update.message.reply_text("Пожалуйста, выберите из предложенных вариантов.")
        return CHOOSING_ROLE
            
    except Exception as e:
        logger.error(f"Error in choose_role: {e}")
        await update.message.reply_text("Произошла ошибка при регистрации.")
        return ConversationHandler.END

# === Сохранение телефона ===
async def save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        phone = None
        
        if update.message.contact:  
            phone = update.message.contact.phone_number
        elif update.message.text == "Пропустить":
            phone = None
        else:
            await update.message.reply_text("Нажмите кнопку отправки телефона или 'Пропустить':")
            return ASK_PHONE

        # ✅ Исправлен баг с сессией
        if phone:
            async with get_async_session() as session:
                await session.execute(
                    sa_update(User)
                    .where(User.id == context.user_data["user_id"])
                    .values(phone_number=phone, updated_at=datetime.utcnow())
                )
                await session.commit()
            
            await update.message.reply_text(
                "Спасибо! Номер телефона сохранён.",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text(
                "Хорошо, пропускаем номер телефона.",
                reply_markup=ReplyKeyboardRemove()
            )

        # ✅ Запрашиваем геолокацию
        return await _ask_for_location(update)
        
    except Exception as e:
        logger.error(f"Error saving phone: {e}")
        await update.message.reply_text("Ошибка при сохранении номера.")
        return ConversationHandler.END

# === Сохранение геолокации ===
async def save_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        is_new_user = context.user_data["is_new_user"]
        session_id = context.user_data["session_id"]
                # Логируем полностью всё сообщение для диагностики
        print("DEBUG_UPDATE:", update)
        print("DEBUG_MESSAGE:", update.message)
        location_saved = False
        
        if update.message.location:
            lat = update.message.location.latitude
            lon = update.message.location.longitude
            point = from_shape(Point(lon, lat), srid=4326)
            
            # ✅ Исправлен баг с сессией
            async with get_async_session() as session:
                await session.execute(
                    sa_update(Session)
                    .where(Session.id == session_id)
                    .values(location=point, updated_at=datetime.utcnow())
                )
                await session.commit()
            
            await update.message.reply_text(
                "Спасибо! Геолокация сохранена.",
                reply_markup=ReplyKeyboardRemove()
            )
            location_saved = True

                   
        elif update.message.text == "Не отправлять":
            await update.message.reply_text(
                "Хорошо, геолокация не сохранена.",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text("Выберите: отправить геолокацию или 'Не отправлять':")
            return ASK_LOCATION
        
        # Финальное сообщение
        if is_new_user:
            await update.message.reply_text("🎉 Регистрация завершена успешно!")
        else:
            await update.message.reply_text(f"👋 Рады видеть вас снова!")
        
        return await _handle_redirect(update, context)
        
    except Exception as e:
        logger.error(f"Error saving location: {e}")
        await update.message.reply_text("Ошибка при сохранении геолокации.")
        return ConversationHandler.END



# === Вспомогательная функция ===
async def _ask_for_location(update):
    """Вспомогательная функция для запроса геолокации"""
    keyboard = [
        [KeyboardButton("📍 Нажмите, чтобы поделиться", request_location=True)], 
        ["Не отправлять"]
    ]
    await update.message.reply_text(
        "Для улучшения поиска поделитесь геолокацией или нажмите 'Не отправлять':",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return ASK_LOCATION



async def _handle_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        role_id = context.user_data.get("role_id")

        if not role_id:
            await update.message.reply_text("⚠️ Ошибка. Начните заново /start")
            return ConversationHandler.END

        if role_id == 1:  # tenant
            keyboard = [[InlineKeyboardButton("🔍 Начать поиск", callback_data="start_search")]]
            prompt = "🏡 Выберите действие:"
        elif role_id == 2:  # owner
            keyboard = [[InlineKeyboardButton("➕ Добавить объект", callback_data="add_object")]]
            prompt = "🏠 Выберите действие:"
        else:
            await update.message.reply_text("⚠️ Неизвестная роль. Начните заново /start")
            return ConversationHandler.END

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(prompt, reply_markup=reply_markup)

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"❌ Ошибка в redirect: {e}")
        await update.message.reply_text("❗ Произошла ошибка при перенаправлении.")
        return ConversationHandler.END

    
#==== Показ объектов лендлорду ===
async def select_owner_objects (update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user_id = update.effective_user.id
    async with get_async_session() as session:
        result_owner = await session.execute(
            select(User).where(User.tg_user_id == tg_user_id, User.role_id == 2)
        )
        owner = result_owner.scalar_one_or_none()
        if not owner:
            await update.message.reply_text("❌ Вы не зарегистрированы как владелец.")
            return CHOOSING_ROLE

        # Получаем активные объекты владельца
        result_apts = await session.execute(
            select(Apartment).options(selectinload(Apartment.booking))
            .where(Apartment.owner_id == owner.id, Apartment.is_active == True)
        )
        apartments = result_apts.scalars().all()

    if not apartments:
        await update.message.reply_text("🏢 У вас нет активных объектов.")
        return CHOOSING_ROLE
    
    context.user_data["owner_objects"] = apartments
    await send_message(update, f"🔍Найдено ваших объектов: {len(apartments)}")

    await show_owner_objects(update,context)
    return VIEW_OBJECTS

async def show_owner_objects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()  # Обязательно!

    data = query.data if query else None
    print("🔁 Callback получен:", data)
    # Получаем список объектов из user_data
    apts = context.user_data.get("owner_objects", [])
    if not apts:
        if query:
            await query.edit_message_text("❌ Список квартир пуст.")
        else:
            await update.message.reply_text("❌ Список квартир пуст.")
        return CHOOSING_ROLE

    # По умолчанию индекс 0
    current_index = 0

    # Парсим индекс из callback_data
    if data:
        if data.startswith("apt_next_") or data.startswith("apt_prev_"):
            try:
                current_index = int(data.split("_")[-1])
            except (ValueError, IndexError):
                await query.message.reply_text("Ошибка индекса. Попробуйте снова.")
                return CHOOSING_ROLE
        elif data.startswith("apt_delete_"):
            try:
                current_apartment = int(data.split("_")[-1])
                tg_user_id = update.effective_user.id
                return await delete_apartment(current_apartment, tg_user_id, update, context)
            except (ValueError, IndexError):
                await query.message.reply_text("Ошибка индекса. Попробуйте снова.")
                return CHOOSING_ROLE
        elif data.startswith("goto_"):
            return await select_owner_orders(update, context)
        elif data == "back_menu":
            await start (update, context)
            return 


    # Ограничиваем индекс допустимым диапазоном
    total = len(apts)
    current_index = max(0, min(current_index, total - 1))

    current_apartment = apts[current_index]

    # Генерируем карточку
    text, markup = prepare_owner_objects_cards(current_apartment, current_index, total)

    if query:
        #await query.answer()  # Обязательно!
        try:
            await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            await query.message.reply_text("Ошибка при отображении карточки.")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")

    return VIEW_OBJECTS    

#=======Проваливаемся в бронирования Лендлорда=======
async def select_owner_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    apartment_id = int(query.data.split("_")[-1])
    async with get_async_session() as session:
    # Получаем активные бронирования по данному объекту
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.apartment)
                .selectinload(Apartment.apartment_type),
                selectinload(Booking.apartment)
                .selectinload(Apartment.owner),
                selectinload(Booking.booking_type)
            )
            .where(Booking.apartment_id == apartment_id)
            .order_by(Booking.status_id.asc(),
                      Booking.total_price.desc())
        )
        result = await session.execute(stmt)
        owner_booking_full = result.scalars().all()


    if not owner_booking_full:
        await update.message.reply_text("🏢 Активных бронирований не найдено.")
        return CHOOSING_ROLE
    
    context.user_data["owner_bookings"] = owner_booking_full
    #await send_message(update, f"ID{apartment_id} 🔍найдено активных бронирований: {len(owner_booking_full)}")

    await show_owner_orders(update,context)
    
    return VIEW_ORDERS

async def show_owner_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()  # Обязательно!

    data = query.data if query else None
    print("🔁 Callback получен:", data)
    # Получаем список объектов из user_data
    bookings = context.user_data.get("owner_bookings", [])
    if not bookings:
        if query:
            await query.edit_message_text("❌ Список бронирований пуст.")
        else:
            await update.message.reply_text("❌ Список бронирований пуст.")
        return CHOOSING_ROLE
    
    # По умолчанию индекс 0
    current_index = 0

    # Парсим индекс из callback_data
    if data:
        if data.startswith("owner_book_next_") or data.startswith("owner_book_prev_"):
            try:
                current_index = int(data.split("_")[-1])
            except (ValueError, IndexError):
                await query.message.reply_text("Ошибка индекса. Попробуйте снова.")
                return CHOOSING_ROLE
        elif data.startswith("back_to_objects"):
            await select_owner_objects (update,context)
            return VIEW_OBJECTS



    # Ограничиваем индекс допустимым диапазоном
    total = len(bookings)
    current_index = max(0, min(current_index, total - 1))

    current_booking = bookings[current_index]

    # Генерируем карточку
    text, markup = prepare_owner_orders_cards(current_booking, current_index, total)

    if query:
        #await query.answer()  # Обязательно!
        try:
            await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            await query.message.reply_text("Ошибка при отображении карточки.")
    else:
        await update.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

    return VIEW_ORDERS   

#======показ бронирований Арендатору=========
async def select_renter_bookings (update: Update, context: ContextTypes.DEFAULT_TYPE):
    ACTIVE_BOOKING_STATUSES = [5, 6]
    tg_user_id = update.effective_user.id
    async with get_async_session() as session:
        result_renter = await session.execute(
            select(User).where(User.tg_user_id == tg_user_id, User.role_id == 1)
        )
        renter = result_renter.scalar_one_or_none()
        if not renter:
            await update.message.reply_text("❌ Возникла проблема. Свяжитесь с администратором /help")


        # Получаем активные бронирования Арендатора
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.apartment)
                .selectinload(Apartment.apartment_type),
                selectinload(Booking.apartment)
                .selectinload(Apartment.owner),
                selectinload(Booking.booking_type)
            )
            .where((Booking.user_id == renter.id)
                &(Booking.status_id.in_(ACTIVE_BOOKING_STATUSES)))
        )
        result = await session.execute(stmt)
        booking_full = result.scalars().all()


    if not booking_full:
        await update.message.reply_text("🏢 Активных бронирований не найдено.")
        return CHOOSING_ROLE
    
    context.user_data["renter_bookings"] = booking_full
    await send_message(update, f"🔍Найдено бронирований: {len(booking_full)}")

    await show_renter_bookings(update,context)
    return VIEW_BOOKINGS

async def show_renter_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()  # Обязательно!

    data = query.data if query else None
    print("🔁 Callback получен:", data)
    # Получаем список объектов из user_data
    bookings = context.user_data.get("renter_bookings", [])
    if not bookings:
        if query:
            await query.edit_message_text("❌ Список бронирований пуст.")
        else:
            await update.message.reply_text("❌ Список бронирований пуст.")
        return CHOOSING_ROLE

    # По умолчанию индекс 0
    current_index = 0

    # Парсим индекс из callback_data
    if data:
        if data.startswith("book_next_") or data.startswith("book_prev_"):
            try:
                current_index = int(data.split("_")[-1])
            except (ValueError, IndexError):
                await query.message.reply_text("Ошибка индекса. Попробуйте снова.")
                return CHOOSING_ROLE


    # Ограничиваем индекс допустимым диапазоном
    total = len(bookings)
    current_index = max(0, min(current_index, total - 1))

    current_booking = bookings[current_index]

    # Генерируем карточку
    text, markup = prepare_renter_bookings_cards(current_booking, current_index, total)

    if query:
        #await query.answer()  # Обязательно!
        try:
            await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            await query.message.reply_text("Ошибка при отображении карточки.")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")

    return VIEW_BOOKINGS   



# === Вспомогательная функция ===

async def send_message(update: Update, text: str):
    """Универсальная отправка сообщения (поддержка Message и CallbackQuery)."""
    if update.message:
        await update.message.reply_text(text)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text)     


async def delete_apartment(apartment_id: int, tg_user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
    ACTIVE_BOOKING_STATUSES = [5, 6]
    async with get_async_session() as session:
        # Получаем квартиру с букингами
        result = await session.execute(
            select(Apartment)
            .options(selectinload(Apartment.booking))
            .where(Apartment.id == apartment_id)
        )
        apartment = result.scalar_one_or_none()

        if not apartment:
            await update.callback_query.message.reply_text("❌ Объект не найден.")
            return VIEW_OBJECTS

        # Проверка на активные бронирования
        has_active = any(b.status_id in ACTIVE_BOOKING_STATUSES for b in apartment.booking)

        if has_active:
            await update.callback_query.message.reply_text(
                "🚫 На данном объекте есть активные бронирования. "
                "Сообщите администратору о вашей проблеме. /help"
            )
            return 

        # Обновление полей
        await session.execute(
            sa_update(Apartment)
            .where(Apartment.id == apartment_id)
            .values(
                is_active=False,
                updated_at=datetime.utcnow(),
                deleted_by=tg_user_id
            )
        )
        await session.commit()

        await update.callback_query.message.reply_text("✅ Объект успешно удалён.")


        return VIEW_OBJECTS

# === Отмена ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Действие отменено. Для продолжения работы нажмите /start",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END