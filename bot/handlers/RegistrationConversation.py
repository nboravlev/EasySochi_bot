from telegram import ReplyKeyboardMarkup, KeyboardButton, Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
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

from bot.utils.user_session import register_user_and_session
from bot.utils.owner_objects_request_from_menu import prepare_owner_objects_cards
from bot.utils.renter_bookings_request_from_menu import prepare_renter_bookings_cards
from bot.utils.booking_chat_message_history import send_booking_chat_history

from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

# === Состояния ===
(CHOOSING_ROLE, 
 ASK_PHONE, 
 ASK_LOCATION,
 VIEW_BOOKINGS,
 VIEW_OBJECTS,
 REPORT_PROBLEM,
 BOOKING_CHAT,
 SHOW_HELP
)= range(8)

# === Роли ===
ROLE_MAP = {
    "🏠 Хочу арендовать жильё": 1,  # tenant
    "🏘 Хочу сдавать жильё": 2     # owner
}

# === Дополнительные действия ===
EXTRA_ACTIONS = {
    "📑 Просмотреть мои бронирования": VIEW_BOOKINGS,
    "🏢 Просмотреть мои объекты": VIEW_OBJECTS,
    "⚠️ Сообщить о проблеме": REPORT_PROBLEM,
    "ℹ️ Подробнее о работе бота": SHOW_HELP
}

# === Старт ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [[btn] for btn in ROLE_MAP.keys()] + [[btn] for btn in EXTRA_ACTIONS.keys()]
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        

        if update.message:
            await update.message.reply_text(
                "Привет! Что вы хотите сделать:",
                reply_markup=reply_markup
            )
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(
                "Выберите действие:",
                reply_markup=reply_markup
            )

        return CHOOSING_ROLE
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        return ConversationHandler.END

# === Выбор роли и регистрация ===
async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            elif next_state == REPORT_PROBLEM:
                await update.message.reply_text("⚠️ Опишите проблему, и я передам сообщение администратору.")
                return REPORT_PROBLEM
            elif next_state == SHOW_HELP:
                keyboard = [
                    [InlineKeyboardButton("📆 Инструкция по бронированию", callback_data="help_booking")],
                    [InlineKeyboardButton("🏠 Инструкция по добавлению объекта", callback_data="help_object")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    "ℹ️ Выберите раздел, по которому нужна помощь:",
                    reply_markup=reply_markup
                )
                return SHOW_HELP


        
        if user_choice in ROLE_MAP:
            role_id = ROLE_MAP[user_choice]
            tg_user = update.effective_user
            bot_id = context.bot.id
            print(f"результат запроса в ТГ{tg_user}")
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
                    [KeyboardButton("📞 Отправить телефон", request_contact=True)], 
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
            await update.message.reply_text("👋 Рады видеть вас снова!")
        
        return await _handle_redirect(update, context)
        
    except Exception as e:
        logger.error(f"Error saving location: {e}")
        await update.message.reply_text("Ошибка при сохранении геолокации.")
        return ConversationHandler.END



# === Вспомогательная функция ===
async def _ask_for_location(update):
    """Вспомогательная функция для запроса геолокации"""
    keyboard = [
        [KeyboardButton("📍 Отправить геолокацию", request_location=True)], 
        ["Не отправлять"]
    ]
    await update.message.reply_text(
        "Для улучшения поиска поделитесь геолокацией или нажмите 'Не отправлять':",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return ASK_LOCATION

from telegram import ReplyKeyboardMarkup, KeyboardButton

async def _handle_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        role_id = context.user_data.get("role_id")

        if not role_id:
            await update.message.reply_text("Ошибка. Начните заново /start")
            return ConversationHandler.END

        if role_id == 1:
            keyboard = [[KeyboardButton("🌍 Начать поиск")]]
        elif role_id == 2:
            keyboard = [[KeyboardButton("🔑 Добавить объект")]]
        else:
            await update.message.reply_text("Неизвестная роль. Начните заново /start")
            return ConversationHandler.END

        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Нажмите, чтобы продолжить:", reply_markup=markup)

    except Exception as e:
        logger.error(f"Error in redirect: {e}")
        await update.message.reply_text("Ошибка перенаправления.")
        return ConversationHandler.END


    
#==== Обработка проблемы ===

async def handle_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):

    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
    if not ADMIN_CHAT_ID:
        raise ValueError("ADMIN_CHAT_ID is not set in .env")
    try:
        user = update.effective_user
        problem_text = update.message.text
        print(f"DEBUG repory_problem sender_id {user.id}")
        # ✅ Формируем сообщение для админов
        admin_message = (
            f"🚨 *Сообщение о проблеме*\n\n"
            f"👤 Пользователь: [{user.first_name}](tg://user?id={user.id})\n"
            f"🆔 TG ID: `{user.id}`\n\n"
            f"📝 Проблема:\n{problem_text}"
        )

        # ✅ Отправляем сообщение в админский чат
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message,
            parse_mode="Markdown"
        )

        # ✅ Отправляем подтверждение пользователю
        await update.message.reply_text(
            "✅ Спасибо! Ваше сообщение передано администратору.\n"
            "Если потребуется, мы свяжемся с вами."
        )

        # ✅ Показываем клавиатуру главного меню
        keyboard = [[btn] for btn in ROLE_MAP.keys()] + [[btn] for btn in EXTRA_ACTIONS.keys()]
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )

        return CHOOSING_ROLE

    except Exception as e:
        logger.error(f"Error in handle_problem: {e}")
        await update.message.reply_text("Произошла ошибка при отправке сообщения. Попробуйте позже.")
        return CHOOSING_ROLE

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
        elif data == "back_menu":
            await start (update, context)


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
       
#======показ бронирований Арендатору=========
async def select_renter_bookings (update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user_id = update.effective_user.id
    async with get_async_session() as session:
        result_renter = await session.execute(
            select(User).where(User.tg_user_id == tg_user_id, User.role_id == 1)
        )
        renter = result_renter.scalar_one_or_none()
        if not renter:
            await update.message.reply_text("❌ Возникла проблема. Свяжитесь с администратором.")
            return REPORT_PROBLEM

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
                &(Booking.status_id.in_([5, 6])))
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
        elif data.startswith("book_message_"):
            try:
                current_booking = int(data.split("_")[-1])
                await send_booking_chat_history(current_booking, update)
                context.user_data["chat_booking_id"] = current_booking
                await query.message.reply_text(
                    f"💬 Вы вошли в чат бронирования №{current_booking}.\n"
                    f"Отправьте свое сообщение."
                )
                return BOOKING_CHAT
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


async def help_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # обязательный ответ на callback

    data = query.data

    buttons = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_menu")]]
    markup = InlineKeyboardMarkup(buttons)

    if data == "help_booking":
        await query.message.reply_text(
            "📆 *Инструкция по бронированию:*\n\n"
            "1. Перейдите в раздел 'Хочу снять жильё';\n"
            "2. Следуйте подсказкам робота;\n"
            "3. Найдите подходящий объект через поиск;\n"
            "4. Нажмите 'Забронировать';\n"
            "5. Дождитесь подтверждения от владельца;\n"
            "6. Общайтесь с ним в чате по бронированию;\n"
            "7. Запросите в чате инструкции по оплате и заселению;\n"
            "8. Все заявки сохраняются в разделе 'Просмотреть мои бронирования';\n"
            "9. Из своей заявки можно вернуться в чат с владельцем для уточнений;\n"
            "10. Если возниктут неразрешимые затруднения, напишите в раздел 'Сообщить о проблеме'.",
            parse_mode="Markdown",
            reply_markup=markup
        )
    elif data == "help_object":
        await query.message.reply_text(
            "🏠 *Инструкция по добавлению объекта:*\n\n"
            "1. Перейдите в раздел 'Хочу сдавать жильё';\n"
            "2. Следуйте подсказкам робота;\n"
            "3. Заполните информацию: название, описание, фото и т.д.;\n"
            "4. При вводе адреса достаточно указать город, улицу и номер дома и выбрать из предложенных роботом вариатов;\n"
            "5. При добавлении изображений дождитесь, пока закончится загрузка - значок часов справа внизу. После загрузки отправьте сообщение 'Готово';\n"
            "6. В поиске пользователю демонстрируется только первое загруженное фото;\n"
            "7. Далее нажмите 'Подтвердить', если все хорошо;\n"
            "8. Нажмите 'Ввести заново', чтобы удалить и ввести заново;\n"
            "9. После создания бронирования вы получите уведомление;\n"
            "10. В теч. суток нужно подтвердить или отклонить с указанием причины;\n"
            "11. После вашего подтверждения у пользователя появится доступ в чат с вами;\n"
            "12. В боте пока нет встроенной функции оплаты, поэтому о способах оплаты вы информируете гостя в этом чате;\n"
            "13. В разделе 'Просмотреть мои объекты' вы сможет просматривать добавленные с текущего аккаунта ТГ объекты;\n"
            "14. Отредактировать пока не получится, только удалить и создать заново;\n"
            "15. Если на объекте есть активные бронирования, то по вопросам редактирования напишите в раздел 'Сообщить о проблеме';\n"
            "16. Чтобы убрать из поиска свой объект на конкретные даты, самостоятельно создайте бронирования на эти даты с подтверждением;\n"
            "17. 25 числа каждого месяца вы получите уведомление о сумме завершенных бронирований по 24 включительно, размере комиссии и инструкцией по оплате."
,
            parse_mode="Markdown",
            reply_markup=markup
        )

    

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
                "Сообщите администратору о вашей проблеме."
                "Просто напишите сообщение и нажмите Отправить, с вами свяжутся"
            )
            return REPORT_PROBLEM

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

        await select_owner_objects(update, context)
        return VIEW_OBJECTS

async def booking_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking_id = context.user_data.get("chat_booking_id")
    if not booking_id:
        return  # пользователь не в контексте чата бронирования


    text = update.message.text
    user_tg_id = update.effective_user.id

    async with get_async_session() as session:
        # 1. Получаем объект бронирования
        result = await session.execute(
            select(Booking).where(Booking.id == booking_id)
        )
        booking = result.scalar_one_or_none()
        if not booking:
            await update.message.reply_text("❌ Бронирование не найдено.")
            return

        # 2. Получаем арендатора (user_id -> tg_user_id)
        result = await session.execute(
            select(User).where(User.id == booking.user_id)
        )
        renter = result.scalar_one_or_none()
        if not renter:
            await update.message.reply_text("❌ Арендатор не найден.")
            return

        renter_id = renter.id
        renter_tg_id = renter.tg_user_id

        # 3. Получаем владельца по apartment.owner_id
        result = await session.execute(
            select(Apartment).where(Apartment.id == booking.apartment_id)
        )
        apartment = result.scalar_one_or_none()
        if not apartment:
            await update.message.reply_text("❌ Объект не найден.")
            return

        owner_id = apartment.owner_id

        result = await session.execute(
            select(User).where(User.id == owner_id)
        )
        owner = result.scalar_one_or_none()
        if not owner:
            await update.message.reply_text("❌ Владелец не найден.")
            return

        owner_tg_id = owner.tg_user_id

        # 4. Определяем отправителя
        sender_id = renter_id if user_tg_id == renter_tg_id else owner_id

        # 5. Сохраняем сообщение
        chat_msg = BookingChat(
            booking_id=booking_id,
            sender_id=sender_id,
            message_text=text[:255],
            created_at=datetime.utcnow()
        )
        session.add(chat_msg)
        await session.commit()

    # 6. Определяем получателя
    recipient_tg_id = owner_tg_id if sender_id == renter_id else renter_tg_id

    # 7. Пересылаем сообщение
    await context.bot.send_message(
        chat_id=recipient_tg_id,
        text=f"💬 Сообщение по бронированию №{booking_id}:\n{text}"
    )


# === Отмена ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Действие отменено. Для продолжения работы нажмите /start",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END