from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from datetime import timedelta

async def send_booking_request_to_owner(bot, booking):
    owner_chat_id = booking.apartment.owner.tg_user_id
    print(f"[DEBUG] Вызов send_booking_request_to_owner для owner_id={owner_chat_id}")
    """
    Отправляет владельцу сообщение о новом бронировании с кнопками подтверждения/отклонения.
    
    :param bot: экземпляр telegram.Bot
    :param booking: объект Booking с подгруженными apartment и owner
    """

    
    timeout_deadline = (booking.created_at + timedelta(hours=27)).strftime("%Y-%m-%d %H:%M")  # N + 3 часа GMT

    # Расчет комиссии
    commission_percent = booking.apartment.reward/100 or 0
    commission_sum = booking.total_price * commission_percent

    # Формируем текст сообщения
    text = (
        f"‼️ <b>Создано новое бронирование</b> ‼️\n\n"
        f"Идентификатор бронирования: <b>{booking.id}</b>\n"
        f"Гость ожидает подтверждения до <b>{timeout_deadline}МСК</b>, "
        f"иначе заявка будет аннулирована.\n\n"
        f"🏠 ID объекта: {booking.apartment.id}\n"
        f"🏠 Адрес: {booking.apartment.short_address}\n"
        f"📅 Заезд: {booking.check_in.strftime('%Y-%m-%d')}\n"
        f"📅 Выезд: {booking.check_out.strftime('%Y-%m-%d')}\n"
        f"👥 Гостей: {booking.guest_count}\n"
        f"💰 Стоимость: {booking.total_price} ₽\n"
        f"💼 Комиссия: {booking.apartment.reward}% = {commission_sum:.0f} ₽\n\n"
        f"ℹ️ Комментарий гостя: {booking.comments or '—'}"
    )

    # Inline кнопки
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"booking_confirm_{booking.id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"booking_decline_8_{booking.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправка сообщения
    await bot.send_message(
        chat_id=owner_chat_id,
        text=text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
