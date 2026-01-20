import random, re
from decimal import Decimal
from typing import Tuple, Optional
from sqlalchemy import select, func
from db.db_async import get_async_session
from db.models import Source, User, Apartment, Booking
from utils.logging_config import (
    structured_logger, 
    log_db_select, 
    log_db_insert, 
    log_db_update,
    log_db_delete,
    LoggingContext,
    monitor_performance
)

RENTER_REWARD = Decimal('0.015')
APPTS_REWARD = Decimal('0.015')

@log_db_insert
async def check_or_create_source(tg_user_id: int, suffix: str | None = None):
    async with get_async_session() as session:
        stmt = select(Source).where(Source.tg_user_id == tg_user_id)
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()

        if source:
            return source

        if not suffix:
            return None  # первый вызов — ещё не принял условия

        # Валидация суффикса
        if not re.match(r"^[a-zA-Z0-9_-]{3,20}$", suffix):
            raise ValueError("Некорректный суффикс")

        # Создание записи
        new_source = Source(tg_user_id=tg_user_id, suffix=suffix)
        session.add(new_source)
        await session.commit()
        await session.refresh(new_source)
        return new_source
    

def validate_suffix(suffix: str) -> Tuple[bool, Optional[str]]:
    suffix = suffix.strip()

    # Длина
    if not (3 <= len(suffix) <= 20):
        return False, f"❌ Длина должна быть от 3 до 20 символов. Сейчас {len(suffix)}."

    # Символы
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", suffix):
        # Найдём первый неподходящий символ
        for ch in suffix:
            if not re.fullmatch(r"[a-zA-Z0-9_-]", ch):
                return False, f"❌ Недопустимый символ: «{ch}»"
        return False, "❌ Содержатся недопустимые символы."

    return True, None

@log_db_select(log_slow_only=True, slow_threshold=0.1)
async def validate_unique_suffix(suffix: str) -> bool:
    """Проверка, что суффикс уникален в таблице sources."""
    async with get_async_session() as session:
        stmt = select(Source).where(Source.suffix == suffix)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is None

    
async def generate_unique_suffix(tg_user_id: int, username: str | None = None, first_name: str | None = None):
    base = None
    if username:
        base = username.lower()
    elif first_name:
        base = re.sub(r"[^a-zA-Z0-9]", "", first_name.lower())  # чистим от лишних символов
    else:
        base = f"user{tg_user_id}"

    candidate = f"{base}{random.randint(100, 999)}"

    # Проверим уникальность
    async with get_async_session() as session:
        stmt = select(Source).where(Source.suffix == candidate)
        result = await session.execute(stmt)
        while result.scalar_one_or_none():
            candidate = f"{base}{random.randint(100, 999)}"
            result = await session.execute(stmt)

    return candidate

@log_db_select(log_slow_only=True, slow_threshold=0.2)
async def get_referral_stats(source_id: int):
    async with get_async_session() as session:
        registrations = await session.scalar(
            select(func.count(User.id)).where(User.source_id == source_id)
        )
        apartments = await session.scalar(
            select(func.count(Apartment.id)).join(User).where(User.source_id == source_id)
        )
        result = await session.execute(
            select(func.count(Booking.id), func.coalesce(func.sum(Booking.total_price), 0))
            .join(User, User.tg_user_id == Booking.tg_user_id)
            .where(User.source_id == source_id)
        )
        row = result.first()

        if row:
            # Unpack the tuple if a row was found
            bookings, amount = row
        else:
            # Assign default values if no row was found
            bookings, amount = 0, 0      
        
        result = await session.execute(
            select(func.count(Booking.id), func.coalesce(func.sum(Booking.total_price), 0))
            .join(Apartment, Apartment.id == Booking.apartment_id)
            .join(User, User.tg_user_id == Apartment.owner_tg_id)
            .where(User.source_id == source_id)
        )
        row = result.first()
        if row:
            appts_bookings, appts_amount = row
        else:
           appts_bookings, appts_amount = 0, 0 

        renter_reward = amount * RENTER_REWARD
        appts_reward = appts_amount * APPTS_REWARD
        return {
            "registrations": registrations or 0,
            "apartments": apartments or 0,
            "renter_bookings": bookings or 0,
            "renter_amount": amount or 0,
            "renter_reward": renter_reward or 0,
            "appts_bookings": appts_bookings or 0,
            "appts_amount": appts_amount or 0,
            "appts_reward": appts_reward or 0
        }
