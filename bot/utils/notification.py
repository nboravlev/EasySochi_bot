from datetime import datetime
from sqlalchemy import select
from telegram import InputFile

from db.db_async import get_async_session
from db.models import User

from utils.logging_config import structured_logger


async def send_mass_notification(bot):
    """
    Рассылка сообщения всем активным пользователям.
    Отправляется картинка + HTML-текст.
    """

    # 🎄 Праздничное сообщение (умеренно, без перегруза)
    message_text = (
        "✨ <b>Уважаемые пользователи!</b> ✨\n\n"
        "🎄 Приближается праздник и мы к вам с подарками:\n"
        "отменяется коммисия за бота <b>на весь 2026 год!</b>! 🎉\n\n"
        "Акция действует для объектов, которые уже добавлены владельцами, "
        "а также для всех новых объектов, добавленных <b>до конца 2025 года</b>.\n\n"
        "🔔 Присоединяйтесь и приглашайте друзей по ссылке:\n"
        "<a href='https://t.me/EasySochi_rent_bot?start=ny2026'>https://t.me/EasySochi_rent_bot?start=ny2026</a>\n\n"
        "С любовью, команда \n"
        "<a href='https://easysochi.pro/'>EASYSOCHI.PRO</a>"
    )

    image_path = "/bot/static/images/image_.png"

    sent = 0
    failed = 0

    # --- Получаем список пользователей ---
    async with get_async_session() as session:
        result = await session.execute(
            select(User.tg_user_id).where(User.is_active == True,
                User.id == 49)
        )
        rows = result.fetchall()
        users = [row.tg_user_id for row in rows]

    if not users:
        structured_logger.info("Рассылка не выполнена — нет активных пользователей")
        return {"sent": 0, "failed": 0}

    # --- Рассылка ---
    for user_id in users:
        try:
            with open(image_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=message_text,
                    parse_mode="HTML"
                )
            sent += 1

        except Exception as e:
            structured_logger.warning(
                "Ошибка отправки уведомления",
                user_id=user_id,
                action="send_failed",
                context={"error": str(e)}
            )
            failed += 1

    structured_logger.info(
        "Рассылка завершена",
        action="mass_notification_done",
        context={"sent": sent, "failed": failed, "timestamp": datetime.utcnow().isoformat()}
    )

    return {"sent": sent, "failed": failed}
