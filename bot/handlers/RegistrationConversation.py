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

from sqlalchemy import update as sa_update, select, desc
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from datetime import datetime
from sqlalchemy.orm import selectinload

from db.db_async import get_async_session

from db.models.users import User
from db.models.sessions import Session
from db.models.roles import Role
from db.models.search_sessions import SearchSession
from db.models.apartments import Apartment
from db.models.bookings import Booking
from db.models.booking_chat import BookingChat

from utils.user_session import get_user_by_tg_id, create_user, create_session
from utils.owner_objects_request_from_menu import prepare_owner_objects_cards
from utils.renter_bookings_request_from_menu import prepare_renter_bookings_cards
from utils.owner_orders_request_from_menu import prepare_owner_orders_cards
from utils.escape import safe_html

from utils.logging_config import log_function_call, LogExecutionTime, get_logger

from dotenv import load_dotenv
import os

logger = get_logger(__name__)

# === Роли ===
ROLE_MAP = {
    "🏠 арендовать жильё": 1,      # tenant
    "🏘 сдавать жильё": 2,          # owner
    "📑 мои бронирования": 4,      # user personal cabinet
    "🏢 мои объекты": 5            # owner personal cabinet
}

WELCOME_PHOTO_URL = "/bot/static/images/welcome.jpg"

WELCOME_TEXT = (
    "Здравствуйте, \n Я Николай Боравлев, программист и спортсмен из Сочи. Автоматизирую процессы с 2023 г.\n\n"
    "EasySochi это платформа для сдачи в аренду и поиску недвижимости в Сочи, коммуникации пользователей и управления своими бронированиями и квартирами.\n"
    "Моя цель - создать альтернативу дорогим агрегаторам, и за счет минимальной комиссии за пользование инструментом предложить пользователям конкурентную цену.\n"
    "В широком смысле, это настраиваемый масштабируемый продукт для управления бизнесом в сфере услуг, аренды, проката и т.п. По вопросам разработки и внедрения для Вашего бизнеса напишите мне в раздел Помощь"
)

# Constants for conversation states  
NAME_REQUEST, ASK_PHONE, MAIN_MENU, VIEW_BOOKINGS, VIEW_OBJECTS, VIEW_ORDERS = range(6)


def chunk_buttons(buttons, n=2):
    """Group buttons into rows of n buttons each"""
    return [buttons[i:i+n] for i in range(0, len(buttons), n)]


@log_function_call(action="user_start_command")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point - check if user exists and route accordingly"""
    user_id = update.effective_user.id if update.effective_user else None
    start_logger = get_logger(__name__, user_id=user_id)
    
    try:
        tg_user = update.effective_user
        
        # Check if user already exists
        user = await get_user_by_tg_id(tg_user.id)
        
        if user is None:
            # New user - start registration
            start_logger.info(f"New user {tg_user.id} starting registration")
            return await begin_registration(update, context, tg_user)
        else:
            # Existing user - show main menu
            start_logger.info(f"Existing user {tg_user.id} accessing main menu")
            return await show_main_menu(update, context, user)
            
    except Exception as e:
        start_logger.error(
            f"Error in start handler: {str(e)}",
            extra={
                'action': 'start_error',
                'user_id': user_id,
                'error_type': type(e).__name__
            },
            exc_info=True
        )
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте позже или обратитесь в поддержку."
        )
        return ConversationHandler.END


async def begin_registration(update: Update, context: ContextTypes.DEFAULT_TYPE, tg_user):
    """Start registration process for new users"""
    try:
        # Store user data for registration process
        context.user_data.update({
            "tg_user": tg_user,
            "registration_step": "name"
        })
        
        # Send welcome message
        with open(WELCOME_PHOTO_URL, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=f"{WELCOME_TEXT}\n\n🎯 Если вы впервые у нас, пройдите короткую регистрацию."
            )
        
        # Ask for first name - with option to use Telegram name
        keyboard = [[KeyboardButton("Использовать никнейм из ТГ")]]
        await update.message.reply_text(
            "Как мы можем к вам обращаться? Напишите ваше имя или выберите вариант ниже:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        return NAME_REQUEST
        
    except Exception as e:
        logger.error(f"Error in begin_registration: {e}")
        await update.message.reply_text("Ошибка при начале регистрации.")
        return ConversationHandler.END
    
async def handle_name_request(update: Update, context: ContextTypes.DEFAULT_TYPE):

    tg_user = context.user_data.get("tg_user")

    first_name = update.message.text.strip()
    if not first_name or first_name.lower() == "использовать никнейм из тг":
        first_name = tg_user.first_name.strip()
    else:
        first_name = safe_html(first_name)

    context.user_data["first_name"] = first_name

    keyboard = [
            [KeyboardButton("📞 Отправить номер телефона", request_contact=True)],
            ["Пропустить"]
        ]
    await update.message.reply_text(
            f"Приятно познакомиться, {first_name}!\n\n"
            "Пожалуйста, поделитесь номером телефона для лучшего сервиса "
            "(или нажмите 'Пропустить'):",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
    
    return ASK_PHONE

async def handle_phone_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number during registration"""
    try:
        phone = None
        
        if update.message.contact:
            phone = update.message.contact.phone_number
        elif update.message.text == "Пропустить":
            phone = None
        else:
            await update.message.reply_text("Пожалуйста, нажмите кнопку отправки телефона или 'Пропустить':")
            return ASK_PHONE

        # Complete user registration
        tg_user = context.user_data.get("tg_user")
        first_name = context.user_data.get("first_name")
        
        user = await create_user(tg_user, first_name, phone)
        
        await update.message.reply_text(
            f"✅ Регистрация завершена!\n"
            f"{'Номер телефона сохранён.' if phone else 'Регистрация без номера телефона.'}",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Show main menu
        return await show_main_menu(update, context, user)
        
    except Exception as e:
        logger.error(f"Error in handle_phone_registration: {e}")
        await update.message.reply_text("Ошибка при сохранении данных.")
        return ConversationHandler.END


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Show main menu with role options"""
    try:
        # Store user data for the session
        context.user_data.update({
            "user_id": user.id,
            "tg_user_id": user.tg_user_id
        })
        
        # Create menu buttons
        all_buttons = list(ROLE_MAP.keys())
        keyboard = chunk_buttons(all_buttons, n=2)
        
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True
        )
        
        welcome_back_msg = f"👋 Добро пожаловать, {user.firstname or 'пользователь'}!\n\nВыберите действие:"
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(welcome_back_msg, reply_markup=reply_markup)
        elif hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(welcome_back_msg, reply_markup=reply_markup)
        else:
            await update.effective_chat.send_message(welcome_back_msg, reply_markup=reply_markup)
        return MAIN_MENU
        
    except Exception as e:
        logger.error(f"Error in show_main_menu: {e}")
        await update.message.reply_text("Ошибка при показе главного меню.")
        return ConversationHandler.END


async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user's menu choice and create appropriate session"""
    try:
        user_choice = update.message.text
        tg_user_id = context.user_data.get("tg_user_id")
        
        if user_choice not in ROLE_MAP:
            await update.message.reply_text("Пожалуйста, выберите из предложенных вариантов.")
            return MAIN_MENU
        
        role_id = ROLE_MAP[user_choice]
        
        # Create session with selected role
        session = await create_session(tg_user_id, role_id)
        
        # Store session info
        context.user_data.update({
            "session_id": session.id,
            "role_id": role_id
        })
        
        # Route based on role
        return await route_by_role(update, context, role_id)
        
    except Exception as e:
        logger.error(f"Error in handle_menu_choice: {e}")
        await update.message.reply_text("Произошла ошибка при обработке выбора.")
        return ConversationHandler.END


async def route_by_role(update: Update, context: ContextTypes.DEFAULT_TYPE, role_id: int):
    """Route user to appropriate flow based on selected role"""
    try:
        await update.message.reply_text("Обрабатываю ваш запрос...", reply_markup=ReplyKeyboardRemove())
        
        if role_id == 1:  # tenant - search for property
            keyboard = [[InlineKeyboardButton("🔍 Начать поиск жилья", callback_data="start_search")]]
            prompt = "🏡 Готов помочь найти аренду в Сочи!"
            
        elif role_id == 2:  # owner - add property  
            keyboard = [[InlineKeyboardButton("➕ Добавить объект", callback_data="add_object")]]
            prompt = "🏠 Готов помочь сдать вашу недвижимость!"
            
        elif role_id == 4:  # user bookings
            await select_renter_bookings(update, context)
            return VIEW_BOOKINGS  # or appropriate state
            
        elif role_id == 5:  # owner objects
            await select_owner_objects(update, context)  
            return VIEW_OBJECTS  # or appropriate state
            
        else:
            await update.message.reply_text("⚠️ Неизвестная ошибка. Начните заново /start")
            return ConversationHandler.END

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(prompt, reply_markup=reply_markup)
        
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in route_by_role: {e}")
        await update.message.reply_text("❗ Произошла ошибка при перенаправлении.")
        return ConversationHandler.END
    
#==== Показ объектов лендлорду ===
async def select_owner_objects (update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user_id = update.effective_user.id
    async with get_async_session() as session:
        # Получаем активные объекты владельца
        result_apts = await session.execute(
            select(Apartment).options(selectinload(Apartment.booking))
            .where(
                Apartment.owner_tg_id == tg_user_id,
                Apartment.is_active == True,
                Apartment.is_draft == False
    )
            .order_by(desc(Apartment.updated_at))
        )
        apartments = result_apts.scalars().all()

    if not apartments:
        await update.message.reply_text("🏢 У вас нет активных объектов.")
        return MAIN_MENU
    
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
        return MAIN_MENU

    # По умолчанию индекс 0
    current_index = 0

    # Парсим индекс из callback_data
    if data:
        if data.startswith("apt_next_") or data.startswith("apt_prev_"):
            try:
                current_index = int(data.split("_")[-1])
            except (ValueError, IndexError):
                await query.message.reply_text("Ошибка индекса. Попробуйте снова.")
                return MAIN_MENU
        elif data.startswith("apt_delete_"):
            try:
                current_apartment = int(data.split("_")[-1])
                tg_user_id = update.effective_user.id
                return await delete_apartment(current_apartment, tg_user_id, update, context)
            except (ValueError, IndexError):
                await query.message.reply_text("Ошибка индекса. Попробуйте снова.")
                return MAIN_MENU
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
        return MAIN_MENU
    
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
        return MAIN_MENU
    
    # По умолчанию индекс 0
    current_index = 0

    # Парсим индекс из callback_data
    if data:
        if data.startswith("owner_book_next_") or data.startswith("owner_book_prev_"):
            try:
                current_index = int(data.split("_")[-1])
            except (ValueError, IndexError):
                await query.message.reply_text("Ошибка индекса. Попробуйте снова.")
                return MAIN_MENU
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
            .where((Booking.tg_user_id == tg_user_id)
                &(Booking.status_id.in_(ACTIVE_BOOKING_STATUSES)))
            .order_by(Booking.created_at.desc())
        )
        result = await session.execute(stmt)
        booking_full = result.scalars().all()


    if not booking_full:
        await update.message.reply_text("🏢 Активных бронирований не найдено.")
        return MAIN_MENU
    
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
        return MAIN_MENU

    # По умолчанию индекс 0
    current_index = 0

    # Парсим индекс из callback_data
    if data:
        if data.startswith("book_next_") or data.startswith("book_prev_"):
            try:
                current_index = int(data.split("_")[-1])
            except (ValueError, IndexError):
                await query.message.reply_text("Ошибка индекса. Попробуйте снова.")
                return MAIN_MENU


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
    context.user_data.clear()
    return ConversationHandler.END