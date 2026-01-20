from datetime import date
from decimal import Decimal
from sqlalchemy import select, func, and_,Numeric, cast
from db.db_async import get_async_session
from db.models import User, Apartment, Booking
from utils.logging_config import structured_logger, LoggingContext

CHAT_ID = 321725128

async def collect_daily_stats(context) -> str:
    """
    Собирает статистику по пользователям, апартаментам и бронированиям.
    Показывает общее количество и прирост за сегодня, а также распределение по статусам.
    """
    today = date.today()
    bot = context.bot

    with LoggingContext("daily_stats_collection") as log_ctx:
        async with get_async_session() as session:
            try:
                # === 1. Пользователи ===
                total_users = await session.scalar(select(func.count(User.id)))
                new_users_today = await session.scalar(
                    select(func.count(User.id)).where(func.date(User.created_at) == today)
                )

                # === 2. Апартаменты ===
                total_apts = await session.scalar(select(func.count(Apartment.id)))
                new_apts_today = await session.scalar(
                    select(func.count(Apartment.id)).where(func.date(Apartment.created_at) == today)
                )

                # === 3. Бронирования ===
                total_bookings = await session.scalar(select(func.count(Booking.id)))
                new_bookings_today = await session.scalar(
                    select(func.count(Booking.id)).where(func.date(Booking.created_at) == today)
                )

                # === 4. Срез по статусам (5=PENDING, 6=CONFIRMED) ===
                # Важно: вычисляем комиссию = total_price * reward / 100
                stmt = (
                    select(
                        Booking.status_id,
                        func.count(Booking.id).label("count"),
                        func.sum(Booking.total_price).label("sum_total"),
                        func.sum(
                            cast(Booking.total_price, Numeric(12, 2)) * (cast(Apartment.reward, Numeric(5, 2)) / 100)
                        ).label("commission"),
                    )
                    .join(Apartment, Apartment.id == Booking.apartment_id)
                    .group_by(Booking.status_id)
                )

                stats_rows = (await session.execute(stmt)).all()
                stats = {row.status_id: row._asdict() for row in stats_rows}

                pending = stats.get(5, {"count": 0, "sum_total": 0, "commission": 0})
                confirmed = stats.get(6, {"count": 0, "sum_total": 0, "commission": 0})

                # === 5. Формируем итоговый текст ===
                text = (
                    f"📊 <b>Ежедневная статистика ({today.strftime('%d.%m.%Y')})</b>\n\n"
                    f"👥 Пользователи: {total_users} <b>(+{new_users_today})</b>\n"
                    f"🏠 Апартаменты: {total_apts} <b>(+{new_apts_today})</b>\n"
                    f"📦 Бронирования: {total_bookings} <b>(+{new_bookings_today})</b>\n\n"
                    f"📋 <b>Бронирования</b>\n"
                    f"⏳ PENDING: {pending['count']} | "
                    f"{pending['sum_total'] or 0:.0f} ₽ | Комиссия {pending['commission'] or 0:.0f} ₽\n"
                    f"✅ CONFIRMED: {confirmed['count']} | "
                    f"{confirmed['sum_total'] or 0:.0f} ₽ | Комиссия {confirmed['commission'] or 0:.0f} ₽\n"
                )

                structured_logger.info(
                    "Daily stats collected successfully",
                    action="daily_stats_ok",
                    context={
                        "users_total": total_users,
                        "apartments_total": total_apts,
                        "bookings_total": total_bookings
                    }
                )

                await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
            
            except Exception as e:
                structured_logger.error(
                    f"Error collecting daily stats: {e}",
                    action="daily_stats_failed",
                    context={"error": str(e)}
                )
                return "⚠️ Ошибка при сборе статистики."

            
