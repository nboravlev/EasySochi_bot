from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from db.db_async import get_async_session
from db.models.apartment_types import ApartmentType
from db.models.apartments import Apartment
from db.models.images import Image
from utils.geocoding import autocomplete_address
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from bot.utils.user_session import register_user_and_session

from bot.utils.full_view_owner import render_apartment_card_full


# Состояния
(
    ADDRESS_INPUT,
    ADDRESS_SELECT,
    APARTMENT_TYPE_SELECTION,
    FLOOR,
    ELEVATOR,
    MAX_GUESTS,
    PETS,
    BALCONY,
    DESCRIPTION,
    PRICE,
    PHOTOS,
    CONFIRMATION
) = range(12)

# ⬇️ Старт
async def start_add_object(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Давайте добавим объект!\nВведите адрес или его часть:"
    )
    return ADDRESS_INPUT

def shorten_address(label: str, keep_parts: int = 4) -> str:
    parts = label.split(", ")
    if len(parts) > keep_parts:
        return ", ".join(parts[-keep_parts:])
    return label

# ⬇️ Выбор из подсказок
async def handle_address_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        index_str = query.data.replace("addr_", "")
        if index_str == "retry":
            await query.edit_message_text("Введите адрес заново:")
            return ADDRESS_INPUT
        
        index = int(index_str)
        selected = context.user_data["addr_candidates"][index]

    except Exception as e:
        print(f"[ERROR] Ошибка при извлечении адреса: {e}")
        await query.edit_message_text("Произошла ошибка при выборе адреса. Попробуйте снова.")
        return ADDRESS_INPUT


    label = selected["label"]
    short_label = shorten_address(label)
    lat = selected["lat"]
    lon = selected["lon"]
    point = from_shape(Point(lon, lat), srid=4326)

    context.user_data["address"] = label
    context.user_data["address_short"] = short_label
    context.user_data["lat"] = lat
    context.user_data["lon"] = lon
    context.user_data["point"] = point

    print(f"[DEBUG] Выбран адрес: {label} ({lat}, {lon})")
    # Показываем кнопки типа объекта прямо здесь
    async with get_async_session() as session:
        result = await session.execute(ApartmentType.__table__.select())
        types = result.fetchall()

        keyboard = [
            [InlineKeyboardButton(t.name, callback_data=str(t.id))] for t in types
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Адрес выбран: {label}\n\nТеперь выберите тип объекта:",
        reply_markup=reply_markup
    )
    return APARTMENT_TYPE_SELECTION  # 👈 тут правильное следующее состояние


# ⬇️ Обработка текста адреса. Блоки местами перепутаны как будто.
async def handle_address_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    suggestions = await autocomplete_address(query)

    if not suggestions:
        await update.message.reply_text("Адрес не найден. Повторите ввод.")
        return ADDRESS_INPUT
    
        # Добавляем короткие адреса
    for s in suggestions:
        s["short_label"] = shorten_address(s["label"])


    context.user_data["addr_candidates"] = suggestions

    keyboard = [
        [InlineKeyboardButton(s["short_label"], callback_data=f"addr_{i}")]
        for i, s in enumerate(suggestions)
    ]
    keyboard.append([InlineKeyboardButton("🔁 Не подходит. Ввести заново.", callback_data="addr_retry")])
    await update.message.reply_text(
        "Выберите ваш адрес:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADDRESS_SELECT


# 2. Обрабатываем выбор типа объекта
async def handle_apartment_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        type_id = int(query.data.replace("type_", ""))
        context.user_data["type_id"] = type_id
    except Exception as e:
        print(f"[ERROR] Не удалось извлечь тип объекта: {e}")
        await query.edit_message_text("Ошибка при выборе типа объекта. Попробуйте снова.")
        return APARTMENT_TYPE_SELECTION

    await query.message.reply_text("Этаж:")
    return FLOOR

# ⬇️ Этаж
async def handle_floor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        floor = int(update.message.text)
        if floor <= 0:
            raise ValueError
        context.user_data["floor"] = floor
    except ValueError:
        await update.message.reply_text("Введите корректное число (>0):")
        return FLOOR

    await update.message.reply_text("Максимум гостей:")
    return MAX_GUESTS

# ⬇️ Максимум гостей
async def handle_maxguests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        max_guests = int(update.message.text)
        if max_guests <= 0:
            raise ValueError
        context.user_data["max_guests"] = max_guests
    except ValueError:
        await update.message.reply_text("Введите разумное число (>0):")
        return MAX_GUESTS

    reply = ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Есть ли лифт в доме?", reply_markup=reply)
    return ELEVATOR

# ⬇️ Лифт → Животные → Балкон
async def handle_elevator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["elevator"] = update.message.text.lower() == "да"
    reply = ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Можно ли с животными?", reply_markup=reply)
    return PETS

async def handle_pets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pets_allowed"] = update.message.text.lower() == "да"
    reply = ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Есть ли балкон?", reply_markup=reply)
    return BALCONY

async def handle_balcony(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["balcony"] = update.message.text.lower() == "да"
    await update.message.reply_text("Введите описание объекта:", reply_markup=ReplyKeyboardRemove())
    return DESCRIPTION

# ⬇️ Описание и цена
async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text("Введите цену за сутки в рублях:")
    return PRICE

async def handle_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text)
        if price <= 0 or price > 99999:
            raise ValueError
        context.user_data["price_per_day"] = price
    except ValueError:
        await update.message.reply_text("Введите число от 0 до 99999:")
        return PRICE

    context.user_data["photos"] = []
    await update.message.reply_text("Загрузите фото объекта не более 10. Отправьте все фото, затем напишите 'Готово'.")
    return PHOTOS

# ⬇️ Фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file_id = photo.file_id

    context.user_data.setdefault("photos", []).append(file_id)

    print(f"[DEBUG] Добавлено фото: {file_id}")
    print(f"[DEBUG] Все фото: {context.user_data['photos']}")

    return PHOTOS

async def handle_photos_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[DEBUG] context.user_data: {context.user_data}")
    user_id = context.user_data.get("user_id")
    
    if not user_id:
        await update.message.reply_text("Ошибка: не найден user_id. Пожалуйста, начните сначала.")
        return ConversationHandler.END
    async with get_async_session() as session:
        apt = Apartment(
            address=context.user_data['address'],
            short_address = context.user_data['address_short'],
            coordinates = context.user_data["point"],
            type_id=context.user_data['type_id'],
            owner_id = user_id,
            floor=context.user_data['floor'],
            max_guests = context.user_data['max_guests'],
            has_elevator=context.user_data['elevator'],
            pets_allowed=context.user_data['pets_allowed'],
            has_balcony=context.user_data['balcony'],
            description=context.user_data['description'],
            price=context.user_data['price_per_day'],
        )
        session.add(apt)
        await session.flush()  # apt.id

        for file_id in context.user_data["photos"]:
            session.add(Image(apartment_id=apt.id, tg_file_id=file_id))

#        await session.commit()
        await session.flush()

        await session.refresh(apt, attribute_names=["apartment_type", "images"])


        text, media, markup = render_apartment_card_full(apt)

        if media:
            await update.message.reply_media_group(media)
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")

        await session.commit()
        #await update.message.reply_text("✅ Объект успешно добавлен в базу!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Отмена добавления объекта.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
