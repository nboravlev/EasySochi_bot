from db.db_async import get_async_session
from db.models import Apartment
from utils.geocoding import parse_point
from utils.logging_config import log_db_select

from telegram import Update
from telegram.ext import ContextTypes,ConversationHandler
from sqlalchemy.future import select
from geoalchemy2.shape import to_shape


async def handle_show_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    apt_id = int(query.data.split("_")[-1])

    async with get_async_session() as session:
        apartment = (await session.execute(
            select(Apartment).where(Apartment.id == apt_id)
        )).scalar_one_or_none()

        if not apartment or not apartment.coordinates:
            await query.message.reply_text("⚠️ У этой квартиры нет координат.")
            return
        
        point = to_shape(apartment.coordinates)
        lat, lon = point.y, point.x
        await query.message.reply_location(latitude=lat, longitude=lon)

        return ConversationHandler.END
"""
        coords = parse_point(apartment.coordinates)
        if not coords:
            await query.message.reply_text("⚠️ Не удалось определить координаты.")
            return

        lat, lon = coords

        await query.message.reply_location(latitude=lat, longitude=lon)
       
    return ConversationHandler.END
"""