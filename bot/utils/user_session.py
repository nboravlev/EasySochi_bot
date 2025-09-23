from sqlalchemy import select, update
from datetime import datetime
from db.db_async import get_async_session
from db.models import (User, Session, Source)
from utils.logging_config import (
    structured_logger, 
    log_db_select, 
    log_db_insert, 
    log_db_update,
    log_db_delete,
    LoggingContext,
    monitor_performance
)

@log_db_select(log_slow_only=True, slow_threshold=0.05)
async def get_user_by_tg_id(tg_user_id: int):
    """Get user by Telegram ID"""
    async with get_async_session() as session:
        result = await session.execute(
            select(User).where(User.tg_user_id == tg_user_id)
        )
        return result.scalars().first()
    
@log_db_select(log_slow_only=True, slow_threshold=0.05)
async def get_source_by_suffix(suffix: str):
    async with get_async_session() as session:
        stmt = select(Source).where(Source.suffix == suffix)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
@log_db_select(log_slow_only=True, slow_threshold=0.05)
async def get_user_by_source_id(source_id: int):
    async with get_async_session() as session:
        stmt = select(User).join(Source, Source.tg_user_id == User.tg_user_id).where(Source.id == source_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

@log_db_insert
async def create_user(tg_user, first_name=None, phone_number=None, source_id: int | None = None):
    """Create new user in database"""
    async with get_async_session() as session:
        user = User(
            tg_user_id=tg_user.id,
            username=tg_user.username,
            firstname=first_name,
            phone_number=phone_number,
            is_bot=tg_user.is_bot,
            created_at=datetime.utcnow(),
            source_id = source_id
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@log_db_insert
async def create_session(tg_user_id: int, role_id: int):
    """Create new session with role"""
    async with get_async_session() as session:
        new_session = Session(
            tg_user_id=tg_user_id,
            role_id=role_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(new_session)
        await session.commit()
        await session.refresh(new_session)
        return new_session