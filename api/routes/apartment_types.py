# api/routes/apartment_types.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.db_async import get_async_session
from db.models.apartment_types import ApartmentType
from schemas.apartment_types import ApartmentTypeOut
from typing import List
from sqlalchemy import select

router = APIRouter()

@router.get("/apartment_types/", response_model=List[ApartmentTypeOut])
async def get_apartment_types(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(ApartmentType))
    return result.scalars().all()
