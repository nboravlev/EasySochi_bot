from db.models.apartments import Apartment
from db.models.bookings import Booking

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)

def prepare_owner_objects_cards(current_apartment: Apartment, current_index: int, total: int) -> tuple[str, str | None, InlineKeyboardMarkup]:
    """Возвращает текст и клавиатуру для карточки."""
    confirmed = sum(1 for b in current_apartment.booking if b.status_id == 6)
    pending = sum(1 for b in current_apartment.booking if b.status_id == 5)

    text = (
        f"🏢 <b>{current_apartment.address}</b>\n"
        f"🏷 Тип: {current_apartment.apartment_type.name}\n"
        f"💰 Цена за ночь: {current_apartment.price} ₽\n"
        f"📝 {current_apartment.description}\n\n"
        f"🏠 Идентификатор объекта: {current_apartment.id}\n"
        f"✅ Бронирование подтверждено: {confirmed}\n"
        f"⏳ Ожидает подтверждения: {pending}\n"
        f"📍 {current_index+1}/{total}"
    )

    # кнопки навигации
    buttons = []
    if current_index > 0:
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"apt_prev_{current_index-1}"))
    if current_index < total - 1:
        buttons.append(InlineKeyboardButton("➡️ Следующий", callback_data=f"apt_next_{current_index+1}"))
    
    buttons = [buttons] if buttons else []
    buttons.append([InlineKeyboardButton("🗑 Удалить объект", callback_data=f"apt_delete_{current_apartment.id}")])
    buttons.append([InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_menu")])

    markup = InlineKeyboardMarkup(buttons)
    
    return text, markup