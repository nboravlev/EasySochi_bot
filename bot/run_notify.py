from datetime import datetime
from utils.notification import send_mass_notification
from utils.logging_config import structured_logger

async def scheduled_notify(context):
    """
    Асинхронная функция для JobQueue.run_daily
    Рассылает сообщение всем пользователям в запланированное время.
    """
    bot = context.bot

    try:
        result = await send_mass_notification(bot)

        if result["sent"] == 0 and result["failed"] == 0:
            structured_logger.info("Нет активных пользователей для новогодней рассылки")
        else:
            structured_logger.info(
                "Рассылка выполнена через планировщик",
                action="scheduled_notify_done",
                context={
                    "sent": result["sent"],
                    "failed": result["failed"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    except Exception as e:
        structured_logger.error(
            f"Ошибка при планировочной рассылке: {e}",
            action="scheduled_notify_failed",
            context={"error": str(e)}
        )
