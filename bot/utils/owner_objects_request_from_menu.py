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
    confirmed = pending = complit = placeholder = confirmed_fund = pending_fund = complit_fund = 0

    for b in current_apartment.booking:
        if b.status_id == 6:  # подтверждено
            confirmed += 1
            confirmed_fund += b.total_price or 0
        elif b.status_id == 5:  # ожидает подтверждения
            pending += 1
            pending_fund += b.total_price or 0
        elif b.status_id == 12:  # завершено
            complit += 1
            complit_fund += b.total_price or 0
        elif b.status_id == 7: #заглушка
            placeholder += 1
    books = confirmed + pending + placeholder

    text = (
        f"🏢 <b>{current_apartment.address}</b>\n\n"
        f"🏷 Тип: {current_apartment.apartment_type.name}\n"
        f"💰 Цена за ночь: {current_apartment.price} ₽\n"
        f"📝 {current_apartment.description}\n"
        f"🏠 Идентификатор объекта: {current_apartment.id}\n\n"
        f"✅ Подтверждено: {confirmed}\n"
        f"📈 На сумму: {confirmed_fund}\n\n"
        f"⏳ Ожидает подтверждения: {pending}\n"
        f"💸 На сумму: {pending_fund}\n\n"
        f"⏳ Завершено: {complit}\n"
        f"💰 На сумму: {complit_fund}\n\n"
        f"📍 {current_index+1} из {total}"
    )

    # кнопки навигации
    buttons = []
    if current_index > 0:
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"apt_prev_{current_index-1}"))
    if current_index < total - 1:
        buttons.append(InlineKeyboardButton("➡️ Следующий", callback_data=f"apt_next_{current_index+1}"))
    
    buttons = [buttons] if buttons else []
    if books > 0:
        buttons.append([InlineKeyboardButton("⚙️ Управление бронированиями", callback_data=f"goto_{current_apartment.id}")])
    buttons.append([InlineKeyboardButton("❄️ Календарь занятости", callback_data=f"placeholder_{current_apartment.id}")])
    buttons.append([InlineKeyboardButton("🔙 В меню", callback_data="back_menu"),
                    InlineKeyboardButton("🗑 Удалить", callback_data=f"apt_delete_{current_apartment.id}")])

    markup = InlineKeyboardMarkup(buttons)
    
    return text, markup