from db.models.apartments import Apartment

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
        f"💰 Цена: {apartment.price_per_day} ₽/ночь"
    )

    photos = [InputMediaPhoto(img.tg_file_id) for img in apartment.images[:10]] if apartment.images else None

    buttons = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_list")],
        [InlineKeyboardButton("✅ Забронировать", callback_data=f"book_{apartment.id}")]
    ]
    markup = InlineKeyboardMarkup(buttons)

    return text, photos, markup
