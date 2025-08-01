from db.models.apartments import Apartment
from db.models.apartment_types import ApartmentType
from db.models.bookings import Booking
from db.models.booking_types import BookingType
from sqlalchemy.orm import selectinload
from db.db_async import get_async_session

from telegram.ext import ContextTypes

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)

from html import escape
from telegram import InputMediaPhoto

def show_booked_appartment(booking: Booking) -> tuple[str, list[InputMediaPhoto] | None]:
    apartment = booking.apartment
    if apartment is None:
        return "<b>❗ Ошибка: данные квартиры не найдены</b>", None

    # Безопасные значения
    short_address = escape(apartment.short_address or "Адрес не указан")
    comments = escape(booking.comments or "Нет комментариев")
    apt_type = escape(getattr(apartment.apartment_type, "name", "Не указан"))

    # Формируем текст
    text = (
        f"<b>{short_address}</b>\n\n"
        f"💬 {comments}\n\n"
        f"🏷️ Тип: {apt_type}\n"
        f"📍 Заезд: {booking.check_in}\n"
        f"📍 Выезд: {booking.check_out}\n"
        f"🧍‍♂️ Гостей: {booking.guest_count}\n"
        f"💰 Стоимость: {booking.total_price} ₽"
    )

    # Подгружаем фото (если есть)
    photos = None
    if getattr(apartment, "images", None):
        valid_photos = [img.tg_file_id for img in apartment.images if getattr(img, "tg_file_id", None)]
        if valid_photos:
            photos = [InputMediaPhoto(file_id) for file_id in valid_photos[:10]]

    return text, photos
