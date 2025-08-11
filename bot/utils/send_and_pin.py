async def send_and_pin_message(bot, chat_id: int, text: str, reply_markup=None):
    """
    Отправляет и закрепляет сообщение в чате.

    :param bot: Экземпляр бота (application.bot)
    :param chat_id: ID чата, где отправляем сообщение
    :param text: Текст сообщения
    :param reply_markup: Опционально — клавиатура или кнопки
    """
    # 1. Отправляем сообщение
    sent_message = await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    # 2. Закрепляем его
    await bot.pin_chat_message(
        chat_id=chat_id,
        message_id=sent_message.message_id,
        disable_notification=False  # True — без уведомления
    )

    return sent_message
