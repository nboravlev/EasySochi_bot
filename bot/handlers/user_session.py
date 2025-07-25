from sqlalchemy import select, update
from datetime import datetime
from db.db_async import get_async_session
from db.models.users import User
from db.models.sessions import Session
from db.models.apartments import Apartment
from db.models.bookings import Booking
from db.models.apartment_types import ApartmentType
from db.models.images import Image
from db.models.booking_types import BookingType

async def register_user_and_session(tg_user, bot_id: int, role_id:int):
    """
    1. Проверяем, есть ли пользователь с telegram_id.
    2. Если нет — создаём запись в public.users.
    3. Всегда создаём новую запись в public.sessions.
    """


    async with get_async_session() as session:
        result = await session.execute(
            select(User).where((User.tg_user_id == tg_user.id)&
            (User.role_id == role_id))
        )
        user = result.scalars().first()

        is_new_user = False

        # 2) Если новый — создаём
        if user is None:
            is_new_user = True
            user = User(
                tg_user_id = tg_user.id,
                username    = tg_user.username,
                role_id = role_id,
                created_at  = datetime.utcnow()
            )
            session.add(user)
            await session.flush()  # чтобы user.id стал доступен
       

        # 3) Создаём новую сессию
        new_session = Session(
            user_id    = user.id,
            created_at = datetime.utcnow(),
            tg_bot_id = bot_id
        )
        session.add(new_session)

        # 4) Фиксируем всё одним коммитом
        await session.commit()
        # Можно вернуть объекты, если нужно
        return user, new_session, is_new_user
