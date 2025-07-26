from db.models.apartments import Apartment
from db.models.apartment_types import ApartmentType
from sqlalchemy.orm import selectinload
from db.db_async import get_async_session

from telegram.ext import ContextTypes

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)

def render_apartment_card_full(apartment: Apartment) -> tuple[str, list[InputMediaPhoto] | None, InlineKeyboardMarkup]:
    text = (
        f"<b>{apartment.short_address}</b>\n\n"
        f"💬 {apartment.description or 'Без описания'}\n\n"
        f"🏷️ Тип: {apartment.apartment_type.name}\n"
        f"📍 Этаж: {apartment.floor}\n"
        f"🧍‍♂️ Гостей: {apartment.max_guests}\n"
        f"💰 Цена: {apartment.price} ₽/ночь"
    )

    photos = [InputMediaPhoto(img.tg_file_id) for img in apartment.images[:10]] if apartment.images else None

    buttons = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_apartment_{apartment.id}")],
        [InlineKeyboardButton("🔄 Внести заново", callback_data=f"redo_apartment_{apartment.id}")]
    ]

    markup = InlineKeyboardMarkup(buttons)

    return text, photos, markup
