from fastapi import FastAPI
from api.routes import geocoding
from api.routes import apartment_types
from db.models.apartment_types import ApartmentType
from db.models.apartments import Apartment
from db.models.users import User
from db.models.bookings import Booking
from db.models.images import Image
from db.models.sessions import Session
from db.models.roles import Role
from db.models.booking_types import BookingType

app = FastAPI(title="Geo API")

# Подключаем маршруты
app.include_router(geocoding.router)

# main.py (если FastAPI запускается отсюда)
app.include_router(apartment_types.router, prefix="/api")
