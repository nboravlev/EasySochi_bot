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
from geoalchemy2.shape import to_shape
from handlers.ShowInfoConversation import info_command
from handlers.ReferralLinkConversation import start_invite

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

from utils.user_session import get_user_by_tg_id, get_source_by_suffix, get_user_by_source_id, create_user, create_session
from utils.owner_objects_request_from_menu import prepare_owner_objects_cards
from utils.renter_bookings_request_from_menu import prepare_renter_bookings_cards
from utils.owner_orders_request_from_menu import prepare_owner_orders_cards
from utils.escape import safe_html
from utils.keyboard_builder import build_calendar, CB_NAV, CB_SELECT
from utils.message_tricks import add_message_to_cleanup, cleanup_messages, send_message
#from utils.delete_apartment import delete_apartment

# Updated logging imports
from utils.logging_config import (
    structured_logger, 
    log_db_select, 
    log_db_insert, 
    log_db_update,
    log_db_delete,
    LoggingContext,
    monitor_performance
)


from dotenv import load_dotenv
import os


# === Роли ===
ROLE_MAP = {
    "🏠 арендовать жильё": 1,      # tenant
    "🏘 сдавать жильё": 2,          # owner
    "📑 мои бронирования": 4,      # user personal cabinet
    "🏢 мои объекты": 5            # owner personal cabinet
}

WELCOME_PHOTO_URL = "/bot/static/images/welcome.jpg"

WELCOME_TEXT = (
    "Здравствуйте, \n Я Николай Боравлев, программист, спортсмен и основатель EasySochi. Автоматизирую процессы с 2023 г.\n\n"
    "EasySochi_rent_bot это платформа для сдачи в аренду и поиску недвижимости в Сочи, коммуникации пользователей и управления своими бронированиями и квартирами.\n"
    "Посетите блок /info чтобы ознакомиться с Инструкциями и Правилами.\n"
    "По вопросам сотрудничества, инвестиций и работы в приложении пишите в раздел /help\n\n"
    "💥💥ВАЖНАЯ НОВОСТЬ:💥💥\n"
    "В блоке /invite создайте собственную реферальную ссылку и заработайте, приглашая пользователей!\n"
)

# Constants for conversation states  
(NAME_REQUEST, 
 ASK_PHONE, 
 MAIN_MENU, 
 VIEW_BOOKINGS, 
 VIEW_OBJECTS, 
 EDIT_OBJECT_PROMPT, 
 EDIT_OBJECT_WAIT_INPUT, 
 VIEW_ORDERS) = range(8)



def chunk_buttons(buttons, n=2):
    """Group buttons into rows of n buttons each"""
    return [buttons[i:i+n] for i in range(0, len(buttons), n)]



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cleanup_messages(context)
    """Entry point - check if user exists and route accordingly"""
    user_id = update.effective_user.id if update.effective_user else None
    args = context.args  # список аргументов после /start
    source_id = None
    print(f"DEBUG_START_ARGUMENT: {args}")

    with LoggingContext("user_start_command", user_id=user_id, 
                       command="start", update_type="telegram") as log_ctx:
    
        try:
            tg_user = update.effective_user

                       # Log user interaction details
            structured_logger.info(
                "User initiated /start command",
                user_id=user_id,
                action="telegram_start_command",
                context={
                    'username': tg_user.username,
                    'first_name': tg_user.first_name,
                    'language_code': tg_user.language_code,
                    'is_bot': tg_user.is_bot
                }
            )
            
            # Check if user already exists
            user = await get_user_by_tg_id(tg_user.id)
            
            if user is None:
                args = context.args  # список аргументов после /start
                source_id = None
                # New user - start registration
                structured_logger.info(
                    "New user starting registration process",
                    user_id=user_id,
                    action="registration_start",
                    context={'tg_username': tg_user.username}
                )
                if args:
                    suffix = args[0]  # например, sochi2025
                    source = await get_source_by_suffix(suffix)
                    if source:
                        source_id = source.id
                        context.user_data["source_tg_id"] = source.tg_user_id
                return await begin_registration(update, context, tg_user,source_id)
            else:
                # Existing user - show main menu
                structured_logger.info(
                    "Existing user accessing main menu",
                    user_id=user_id,
                    action="main_menu_access",
                    context={
                        'user_db_id': user.id,
                        'user_name': user.firstname,
                        'last_login': user.updated_at.isoformat() if user.updated_at else None
                    }
                )
                return await show_main_menu(update, context, user)
                
        except Exception as e:
                # LoggingContext will automatically log the error with full context
                structured_logger.error(
                    f"Critical error in start handler: {str(e)}",
                    user_id=user_id,
                    action="start_command_error",
                    exception=e,
                    context={
                        'tg_user_id': user_id,
                        'error_type': type(e).__name__
                    }
                )
                await update.message.reply_text(
                    "Произошла ошибка. Попробуйте позже или обратитесь в поддержку."
                )
                return ConversationHandler.END


async def begin_registration(update: Update, context: ContextTypes.DEFAULT_TYPE, tg_user,source_id):
    """Start registration process for new users"""
    user_id = tg_user.id
    source_id = source_id

    with LoggingContext("registration_flow", user_id=user_id, 
                    step="begin", process="user_registration") as log_ctx:
        try:
            # Store user data for registration process
            context.user_data.update({
                "tg_user": tg_user,
                "source_id": source_id,
                "registration_step": "name"
            })
            structured_logger.info(
                "Registration process initiated",
                user_id=user_id,
                action="registration_begin",
                context={
                    'tg_username': tg_user.username,
                    'tg_first_name': tg_user.first_name,
                    'has_profile_photo': tg_user.has_profile_photo if hasattr(tg_user, 'has_profile_photo') else None
                }
            )
            try:
            # Send welcome message
                with open(WELCOME_PHOTO_URL, "rb") as f:
                    await update.message.reply_photo(
                        photo=f,
                        caption=f"{WELCOME_TEXT}\n\n🎯 Если вы впервые у нас, пройдите короткую регистрацию."
                    )
                structured_logger.debug(
                    "Welcome photo sent successfully",
                    user_id=user_id,
                    action="welcome_photo_sent"
                )
            except FileNotFoundError as e:
                structured_logger.warning(
                    f"Welcome photo not found: {WELCOME_PHOTO_URL}",
                    user_id=user_id,
                    action="welcome_photo_missing",
                    exception=e
                )
                await update.message.reply_text(f"{WELCOME_TEXT}\n\n🎯 Если вы впервые у нас, пройдите короткую регистрацию.")
                
            # Ask for first name - with option to use Telegram name
            keyboard = [[KeyboardButton("Использовать никнейм из ТГ")]]
            await update.message.reply_text(
                "Как к вам обращаться? Напишите ваше имя или выберите вариант ниже:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            )
            return NAME_REQUEST
            
        except Exception as e:
            structured_logger.error(
                f"Error in begin_registration: {str(e)}",
                user_id=user_id,
                action="registration_begin_error",
                exception=e
            )
            await update.message.reply_text("Ошибка при начале регистрации.")
            return ConversationHandler.END
    
async def handle_name_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle name input during registration"""
    tg_user = context.user_data.get("tg_user")
    user_id = tg_user.id if tg_user else None
    
    with LoggingContext("registration_name_step", user_id=user_id) as log_ctx:
        try:
            first_name = update.message.text.strip()
            original_input = first_name
            
            if not first_name or first_name.lower() == "использовать никнейм из тг":
                first_name = tg_user.first_name.strip()
                name_source = "telegram_profile"
            else:
                first_name = safe_html(first_name)
                name_source = "user_input"

            context.user_data["first_name"] = first_name
            
            structured_logger.info(
                "User name collected during registration",
                user_id=user_id,
                action="registration_name_collected",
                context={
                    'name_source': name_source,
                    'name_length': len(first_name),
                    'original_input': original_input[:50],  # Limit for privacy
                    'sanitized_name': first_name[:50]
                }
            )

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
            
        except Exception as e:
            structured_logger.error(
                f"Error in handle_name_request: {str(e)}",
                user_id=user_id,
                action="registration_name_error",
                exception=e
            )
            await update.message.reply_text("Ошибка при обработке имени.")
            return ConversationHandler.END
        
async def handle_phone_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number during registration"""
    tg_user = context.user_data.get("tg_user")
    user_id = tg_user.id if tg_user else None
    source_id = context.user_data.get("source_id")
    source_tg_id = context.user_data.get("source_tg_id")
    
    with LoggingContext("registration_phone_step", user_id=user_id) as log_ctx:
        try:
            phone = None
            phone_source = None
            
            if update.message.contact:
                phone = update.message.contact.phone_number
                phone_source = "telegram_contact"
                structured_logger.info(
                    "Phone number provided via Telegram contact",
                    user_id=user_id,
                    action="phone_via_contact",
                    context={'phone_country_code': phone[:3] if phone else None}
                )
            elif update.message.text == "Пропустить":
                phone = None
                phone_source = "skipped"
                structured_logger.info(
                    "User skipped phone number entry",
                    user_id=user_id,
                    action="phone_skipped"
                )
            else:
                await update.message.reply_text("Пожалуйста, нажмите кнопку отправки телефона или 'Пропустить':")
                return ASK_PHONE

            # Complete user registration
            first_name = context.user_data.get("first_name")
            registration_start = context.user_data.get("registration_start_time")
            
            # Calculate registration duration
            if registration_start:
                start_time = datetime.fromisoformat(registration_start)
                duration = (datetime.utcnow() - start_time).total_seconds()
            else:
                duration = None
            
            structured_logger.info(
                "Starting user creation in database",
                user_id=user_id,
                action="user_creation_start",
                context={
                    'has_phone': phone is not None,
                    'phone_source': phone_source,
                    'registration_duration': duration
                }
            )
            
            # This function should have @log_db_insert decorator
            user = await create_user(tg_user, first_name, phone,source_id)
            # Уведомление о регистрации по рефералке
            print(f"DEBUG_user_SOURCE_ID: {user.source_id} and source_tg_id: {source_tg_id}")
            if (user.source_id and source_tg_id):
                inviter = await get_user_by_source_id(user.source_id)  # нужна helper-функция
                inviter_name = f"@{inviter.username}" if inviter and inviter.username else f"пользоватлеля ИД @{inviter.tg_user_id}"
                await update.message.reply_text(
                    f"🎉 Вы успешно зарегистрировались по приглашению {inviter_name}!"
                )
            
            # Log successful registration
            structured_logger.info(
                "User registration completed successfully",
                user_id=user_id,
                action="registration_completed",
                context={
                    'new_user_db_id': user.id,
                    'user_name': user.firstname,
                    'referral': user.source_id or None,
                    'has_phone': user.phone_number is not None,
                    'registration_duration': duration,
                    'total_users_count': None  # Could add a count query here
                }
            )
            
            msg=await update.message.reply_text(
                f"✅ Регистрация завершена!\n"
                f"{'Номер телефона сохранён.' if phone else 'Регистрация без номера телефона.'}",
                reply_markup=ReplyKeyboardRemove()
            )
            await add_message_to_cleanup(context,msg.chat_id,msg.message_id)
            # Show main menu
            return await show_main_menu(update, context, user)
            
        except Exception as e:
            structured_logger.error(
                f"Error in handle_phone_registration: {str(e)}",
                user_id=user_id,
                action="registration_phone_error",
                exception=e,
                context={
                    'phone_provided': update.message.contact is not None,
                    'message_text': update.message.text[:50] if update.message.text else None
                }
            )
            await update.message.reply_text("Ошибка при сохранении данных.")
            return ConversationHandler.END


@monitor_performance(threshold=1.0)  # Log if menu generation takes > 1 second
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user=None):
    """Show main menu with role options"""
    if user:
        tg_user_id = user.tg_user_id
        user_id = user.id
        user_name = user.firstname
    else:
       tg_user_id = update.effective_user.id
       user_id = None
       user_name = None
       await cleanup_messages(context)
    
    with LoggingContext("main_menu_display", tg_user_id=tg_user_id, 
                       user_id=user_id)  as log_ctx:
        try:
            # Store user data for the session
            context.user_data.update({
                "user_id": user_id,
                "tg_user_id": tg_user_id
            })
            
            structured_logger.info(
                "Displaying main menu to user",
                user_id=user_id,
                action="main_menu_shown",
                context={
                    'user_db_id': user_id,
                    'user_name': user_name,
                    'available_roles': list(ROLE_MAP.keys()),
                    'menu_options_count': len(ROLE_MAP)
                }
            )
            
            # Create menu buttons
            all_buttons = list(ROLE_MAP.keys())
            keyboard = chunk_buttons(all_buttons, n=2)
            
            reply_markup = ReplyKeyboardMarkup(
                keyboard,
                one_time_keyboard=True,
                resize_keyboard=True
            )
            
                    # текст зависит от источника
            if update.callback_query:
                await update.callback_query.answer()
                text = "Выберите действие:"
            else:
                text = f"👋 Добро пожаловать, {user_name or 'пользователь'}!\n\nВыберите действие:"

            # всегда можно использовать effective_message
            msg = await update.effective_message.reply_text(text, reply_markup=reply_markup)
            await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
            
            return MAIN_MENU
            
        except Exception as e:
            structured_logger.error(
                f"Error in show_main_menu: {str(e)}",
                user_id=user_id,
                action="main_menu_error",
                exception=e,
                context={'user_db_id': user.id}
            )
            await update.message.reply_text("Ошибка при показе главного меню.")
            return ConversationHandler.END

async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user's menu choice and create appropriate session"""
    user_choice = update.message.text
    tg_user_id = context.user_data.get("tg_user_id")
    user_db_id = context.user_data.get("user_id")
    
    with LoggingContext("menu_choice_processing", user_id=tg_user_id,
                       user_db_id=user_db_id, choice=user_choice) as log_ctx:
        try:
            if user_choice not in ROLE_MAP:
                structured_logger.warning(
                    f"Invalid menu choice: {user_choice}",
                    user_id=tg_user_id,
                    action="invalid_menu_choice",
                    context={
                        'invalid_choice': user_choice,
                        'valid_options': list(ROLE_MAP.keys())
                    }
                )
                await update.message.reply_text("Пожалуйста, выберите из предложенных вариантов.")
                return MAIN_MENU
            
            role_id = ROLE_MAP[user_choice]
            
            structured_logger.info(
                f"User selected menu option: {user_choice}",
                user_id=tg_user_id,
                action="menu_choice_made",
                context={
                    'choice': user_choice,
                    'role_id': role_id,
                    'user_db_id': user_db_id
                }
            )
            
            # Create session with selected role (this should have @log_db_insert)
            session = await create_session(tg_user_id, role_id)
            
            # Store session info
            context.user_data.update({
                "session_id": session.id,
                "role_id": role_id
            })
            
            structured_logger.info(
                "User session created successfully",
                user_id=tg_user_id,
                action="session_created",
                context={
                    'session_id': session.id,
                    'role_id': role_id,
                    'role_name': user_choice
                }
            )
            
            # Route based on role
            return await route_by_role(update, context, role_id)
            
        except Exception as e:
            structured_logger.error(
                f"Error in handle_menu_choice: {str(e)}",
                user_id=tg_user_id,
                action="menu_choice_error",
                exception=e,
                context={
                    'user_choice': user_choice,
                    'user_db_id': user_db_id
                }
            )
            await update.message.reply_text("Произошла ошибка при обработке выбора.")
            return ConversationHandler.END

async def route_by_role(update: Update, context: ContextTypes.DEFAULT_TYPE, role_id: int):
    """Route user to appropriate flow based on selected role"""
    tg_user_id = context.user_data.get("tg_user_id")
    session_id = context.user_data.get("session_id")
    
    with LoggingContext("role_routing", user_id=tg_user_id, 
                       role_id=role_id, session_id=session_id) as log_ctx:
        try:
            msg = await update.message.reply_text("Обрабатываю ваш запрос...", reply_markup=ReplyKeyboardRemove())
            await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
            if role_id == 1:  # tenant - search for property
                keyboard = [[InlineKeyboardButton("🔍 Начать поиск жилья", callback_data="start_search")]]
                prompt = "🏡 Готов помочь найти аренду в Сочи!"
                next_action = "property_search"
                
            elif role_id == 2:  # owner - add property  
                keyboard = [[InlineKeyboardButton("➕ Добавить объект", callback_data="add_object")]]
                prompt = "🏠 Готов помочь сдать вашу недвижимость!"
                next_action = "property_add"
                
            elif role_id == 4:  # user bookings
                structured_logger.info(
                    "Routing to renter bookings view",
                    user_id=tg_user_id,
                    action="route_to_bookings",
                    context={'session_id': session_id}
                )
                await select_renter_bookings(update, context)
                return VIEW_BOOKINGS
                
            elif role_id == 5:  # owner objects
                structured_logger.info(
                    "Routing to owner objects view",
                    user_id=tg_user_id,
                    action="route_to_objects",
                    context={'session_id': session_id}
                )
                await select_owner_objects(update, context)  
                return VIEW_OBJECTS
            else:
                structured_logger.warning(
                    f"Unknown role_id: {role_id}",
                    user_id=tg_user_id,
                    action="unknown_role_error",
                    context={'role_id': role_id, 'session_id': session_id}
                )
                await update.message.reply_text("⚠️ Неизвестная ошибка. Начните заново /start")
                return ConversationHandler.END

            # Log successful routing for inline keyboard options
            structured_logger.info(
                f"User routed to {next_action} flow",
                user_id=tg_user_id,
                action=f"route_to_{next_action}",
                context={
                    'role_id': role_id,
                    'session_id': session_id,
                    'next_step': next_action
                }
            )

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(prompt, reply_markup=reply_markup)
            
            return ConversationHandler.END

        except Exception as e:
            structured_logger.error(
                f"Error in route_by_role: {str(e)}",
                user_id=tg_user_id,
                action="role_routing_error",
                exception=e,
                context={'role_id': role_id, 'session_id': session_id}
            )
            await update.message.reply_text("❗ Произошла ошибка при перенаправлении.",reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    
#==== Показ объектов лендлорду ===
@log_db_select(log_slow_only=True, slow_threshold=0.2)
async def select_owner_objects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select owner objects with comprehensive logging"""
    tg_user_id = update.effective_user.id
    with LoggingContext("owner_objects_query", user_id=tg_user_id) as log_ctx:
        async with get_async_session() as session:
            # This database query will be automatically logged if slow
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

        structured_logger.info(
            f"Owner objects query completed: {len(apartments)} apartments found",
            user_id=tg_user_id,
            action="owner_objects_loaded",
            context={
                'apartments_count': len(apartments),
                'has_apartments': len(apartments) > 0
            }
        )

        if not apartments:
            structured_logger.info(
                "No active apartments found for owner",
                user_id=tg_user_id,
                action="no_owner_objects",
            )
            await update.message.reply_text("🏢 У вас нет активных объектов.",reply_markup=ReplyKeyboardRemove())
            return MAIN_MENU
        
        context.user_data["owner_objects"] = apartments
        msg = await send_message(update, f"🔍Найдено ваших объектов: {len(apartments)}",reply_markup=ReplyKeyboardRemove())
        await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
        await show_owner_objects(update, context)
        return VIEW_OBJECTS

async def show_owner_objects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()  # ответ на callback

    apts = context.user_data.get("owner_objects", [])
    if not apts:
        msg = "❌ Список квартир пуст."
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return MAIN_MENU

    # По умолчанию показываем первую квартиру
    current_index = 0
    data = query.data if query else None

    if data:
        try:
            if data.startswith(("apt_next_", "apt_prev_")):       
                current_index = int(data.split("_")[-1])
            elif data.startswith("placeholder"):
                await ConversationHandler.END
        except (ValueError, IndexError):
            await query.message.reply_text("Ошибка индекса. Попробуйте снова.")
            return MAIN_MENU

    # Ограничиваем индекс допустимым диапазоном
    total = len(apts)
    current_index = max(0, min(current_index, total - 1))

    current_apartment = apts[current_index]

    # Генерируем карточку
    text, markup = prepare_owner_objects_cards(current_apartment, current_index, total)

    if query:
        #await query.answer()  # Обязательно!
        try:
            msg = await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
            await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
        except Exception as e:
            await query.message.reply_text("Ошибка при отображении карточки.")
    else:
        msg = await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
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
        await update.message.reply_text("🏢 Активных бронирований не найдено.",reply_markup=ReplyKeyboardRemove())
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


    # Ограничиваем индекс допустимым диапазоном
    total = len(bookings)
    current_index = max(0, min(current_index, total - 1))

    current_booking = bookings[current_index]

    # Генерируем карточку
    text, markup = prepare_owner_orders_cards(current_booking, current_index, total)

    if query:
        #await query.answer()  # Обязательно!
        try:
            msg = await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            msg = await query.message.reply_text("Ошибка при отображении карточки.")
    else:
        msg = await update.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
    return VIEW_ORDERS

#======редактирование карточки квартиры=========
async def handle_apartment_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tg_user_id = update.effective_user.id
    apartment_id = int(query.data.split("_")[-1])

    with LoggingContext("apartment_upgrade_init", user_id=tg_user_id, apartment_id=apartment_id):
        async with get_async_session() as session:
            result = await session.execute(
                select(Apartment).where(Apartment.id == apartment_id)
            )
            apartment = result.scalar_one_or_none()

            if not apartment:
                structured_logger.warning(
                    f"Apartment {apartment_id} not found for upgrade.",
                    user_id=tg_user_id,
                    action="apartment_upgrade_not_found",
                    context={'apartment_id': apartment_id}
                )
                await query.message.edit_text("❌ Объект не найден.")
                return VIEW_OBJECTS

            if apartment.owner_tg_id != tg_user_id:
                structured_logger.warning(
                    f"Unauthorized edit attempt by user {tg_user_id}",
                    user_id=tg_user_id,
                    action="unauthorized_apartment_edit_attempt",
                    context={'apartment_id': apartment_id}
                )
                await query.message.edit_text("🚫 У вас нет прав для редактирования этого объекта.")
                return VIEW_OBJECTS

            structured_logger.info(
                "User initiated apartment price edit.",
                user_id=tg_user_id,
                action="apartment_upgrade_start",
                context={'apartment_id': apartment_id, 'current_price': apartment.price}
            )

            # Сохраняем id квартиры для последующих шагов
            context.user_data["edit_apartment_id"] = apartment_id

            text = (
                f"🛠 Вы можете отредактировать только <b>стоимость</b> объекта.\n\n"
                f"💰 Текущая цена: <b>{apartment.price} ₽/ночь</b>\n\n"
                f"Выберите действие:"
            )

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✏️ Редактировать", callback_data="edit_price_start"),
                    InlineKeyboardButton("🔙 Вернуться назад", callback_data="back_to_objects")
                ]
            ])

            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            return EDIT_OBJECT_PROMPT
        
async def handle_edit_price_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.edit_text(
        "💬 Введите новую стоимость в рублях (только число):",
        reply_markup=None
    )
    return EDIT_OBJECT_WAIT_INPUT

async def handle_new_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user_id = update.effective_user.id
    new_price_text = update.message.text.strip()
    apartment_id = context.user_data.get("edit_apartment_id")

    with LoggingContext("apartment_price_edit", user_id=tg_user_id, apartment_id=apartment_id):
        try:
            new_price = float(new_price_text)
            if new_price <= 0:
                raise ValueError("Price must be positive.")
        except ValueError:
            structured_logger.warning(
                "Invalid price input.",
                user_id=tg_user_id,
                action="invalid_price_input",
                context={'input_value': new_price_text}
            )
            await update.message.reply_text("❌ Введите корректное положительное число.")
            return "EDIT_PRICE_WAIT_INPUT"

        async with get_async_session() as session:
            result = await session.execute(
                select(Apartment).where(Apartment.id == apartment_id)
            )
            apartment = result.scalar_one_or_none()

            if not apartment:
                await update.message.reply_text("⚠️ Объект не найден.")
                return VIEW_OBJECTS

            if apartment.owner_tg_id != tg_user_id:
                await update.message.reply_text("🚫 У вас нет прав для изменения этого объекта.")
                return VIEW_OBJECTS

            # Обновляем цену
            old_price = apartment.price
            apartment.price = new_price
            apartment.updated_at = datetime.utcnow()
            await session.commit()

            structured_logger.info(
                f"Apartment price updated from {old_price} to {new_price}",
                user_id=tg_user_id,
                action="apartment_price_updated",
                context={
                    'apartment_id': apartment_id,
                    'old_price': old_price,
                    'new_price': new_price
                }
            )

            # Уведомляем пользователя и возвращаем к списку
            await update.message.reply_text(
                f"✅ Стоимость обновлена: <b>{new_price:.0f} ₽/ночь</b>",
                parse_mode="HTML"
            )

            # Сразу обновляем карточки
            await select_owner_objects(update, context)
            return VIEW_OBJECTS
        
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
    msg = await send_message(update, f"🔍Найдено бронирований: {len(booking_full)}")
    await add_message_to_cleanup(context, msg.chat_id, msg.message_id)

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
            msg = await query.edit_message_text("❌ Список бронирований пуст.")
            await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
        else:
            msg = await update.message.reply_text("❌ Список бронирований пуст.")
            await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
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
            msg = await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
            await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
        except Exception as e:
            await query.message.reply_text("Ошибка при отображении карточки.")
    else:
        msg = await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        await add_message_to_cleanup(context, msg.chat_id, msg.message_id)

    return VIEW_BOOKINGS   


#=======Отмена удаления====
async def cancel_delete_apartment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    try:
        await query.delete_message()   # Полностью удаляет сообщение с кнопками
    except Exception:
        # fallback: если удалить нельзя, то просто убираем кнопки
        await query.edit_message_reply_markup(reply_markup=None)

    return VIEW_OBJECTS

#=======подтверждение удаления =======

async def confirm_delete_apartment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    apartment_id = int(query.data.split("_")[-1])

    keyboard = [
        [
            InlineKeyboardButton("❌ Удалить", callback_data=f"delete_confirm_{apartment_id}"),
            InlineKeyboardButton("↩️ Отмена", callback_data="delete_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        f"Вы уверены, что хотите удалить объект {apartment_id}?",
        reply_markup=reply_markup
    )
    return VIEW_OBJECTS

#=======подтверждение получено ==========
async def delete_apartment_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    apartment_id = int(query.data.split("_")[-1])
    tg_user_id = update.effective_user.id

    ACTIVE_BOOKING_STATUSES = [5, 6]
    
    with LoggingContext("apartment_deletion", user_id=tg_user_id, 
                       apartment_id=apartment_id) as log_ctx:
        
        structured_logger.warning(
            f"User attempting to delete apartment {apartment_id}",
            user_id=tg_user_id,
            action="apartment_deletion_attempt",
            context={'apartment_id': apartment_id}
        )
        
        async with get_async_session() as session:
            # Check apartment and bookings
            result = await session.execute(
                select(Apartment)
                .options(selectinload(Apartment.booking))
                .where(Apartment.id == apartment_id)
            )
            apartment = result.scalar_one_or_none()

            if not apartment:
                structured_logger.warning(
                    f"Apartment {apartment_id} not found for deletion",
                    user_id=tg_user_id,
                    action="apartment_not_found",
                    context={'apartment_id': apartment_id}
                )
                await update.callback_query.message.reply_text("❌ Объект не найден.")
                return VIEW_OBJECTS

            # Check for active bookings
            active_bookings = [b for b in apartment.booking if b.status_id in ACTIVE_BOOKING_STATUSES]
            
            if active_bookings:
                structured_logger.warning(
                    f"Cannot delete apartment {apartment_id} - has active bookings",
                    user_id=tg_user_id,
                    action="apartment_deletion_blocked",
                    context={
                        'apartment_id': apartment_id,
                        'active_bookings_count': len(active_bookings),
                        'booking_ids': [b.id for b in active_bookings]
                    }
                )
                msg = await update.callback_query.message.reply_text(
                    "🚫 На данном объекте есть активные бронирования. "
                    "Сообщите администратору об этой ситуации. /help"
                )
                await add_message_to_cleanup(context, msg.chat_id, msg.message_id)
                return VIEW_OBJECTS

            # Perform soft deletion
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

            structured_logger.info(
                f"Apartment {apartment_id} successfully deleted",
                user_id=tg_user_id,
                action="apartment_deleted",
                context={
                    'apartment_id': apartment_id,
                    'apartment_title': apartment.short_address if apartment.short_address else None,
                    'deletion_type': 'soft_delete'
                }
            )
            await update.callback_query.message.edit_text("❌ Объект успешно удалён.",
                                                            reply_markup=None)
            return VIEW_OBJECTS


#=======показ на карте арендатору=====
async def handle_show_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    source,_,_,apt_id = query.data.split("_")
    
    request_source = str(source)
    apt_id = int(apt_id)


    async with get_async_session() as session:
        apartment = (
            await session.execute(select(Apartment).where(Apartment.id == apt_id))
        ).scalar_one_or_none()

        if not apartment or not apartment.coordinates:
            await query.message.reply_text("⚠️ Ошибка карты: координаты отсутствуют.")
            if request_source == "owner":
                return VIEW_OBJECTS
            else:
                return VIEW_BOOKINGS

        # Преобразуем в координаты
        point = to_shape(apartment.coordinates)
        lat, lon = point.y, point.x

        # Проверяем, показывалась ли уже карта
        previous_msg_id = context.user_data.get("map_message_id")
        structured_logger.info(f"Map request from menu for apartment {apt_id}",
                           user_id = update.effective_user.id,
                           action = "Show map from menu",
                           context = {
                               'Adress':apartment.short_address,
                               'source': request_source,
                               'prev_msg':previous_msg_id
                           }
        )

        if previous_msg_id:
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=previous_msg_id)
            except Exception:
                pass

        msg = await query.message.reply_location(latitude=lat, longitude=lon)
        context.user_data["map_message_id"] = msg.message_id

                # --- Возврат состояния в зависимости от источника ---
        print(f"DEBUG_FROM_where_MAP_requested: {request_source}")
        if request_source == "owner":
            return VIEW_OBJECTS
        else:
            return VIEW_BOOKINGS    

# === Отмена ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation with logging"""
    user_id = update.effective_user.id if update.effective_user else None
    
    structured_logger.info(
        "User cancelled conversation",
        user_id=user_id,
        action="conversation_cancelled",
        context={
            'conversation_state': context.user_data.get('registration_step'),
            'session_id': context.user_data.get('session_id')
        }
    )
    
    await update.message.reply_text(
        "❌ Действие отменено. Для продолжения работы нажмите /start",
        reply_markup=ReplyKeyboardRemove()
    )
    await cleanup_messages(context)
    context.user_data.clear()
    return ConversationHandler.END

async def info_and_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершает диалог и вызывает info_command."""
    await info_command(update, context)
    return ConversationHandler.END

async def invite_and_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершает диалог и вызывает info_command."""
    await start_invite(update, context)
    return ConversationHandler.END