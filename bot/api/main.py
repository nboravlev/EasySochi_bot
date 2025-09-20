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

# Import logging components
from utils.logging_config import LoggingMiddleware, setup_logging, structured_logger

app = FastAPI(title="Geo API")

# Setup logging on startup
@app.on_event("startup")
async def startup_event():
    setup_logging(
        log_dir="/app/logs",
        log_level="INFO",
        enable_console=True
    )
    
    structured_logger.info(
        "FastAPI application starting up",
        action="app_startup",
        context={
            'app_title': "Geo API",
            'routes_count': len(app.routes)
        }
    )

@app.on_event("shutdown") 
async def shutdown_event():
    structured_logger.info(
        "FastAPI application shutting down",
        action="app_shutdown"
    )

# Add logging middleware FIRST (before routes)
app.add_middleware(LoggingMiddleware)

# Подключаем маршруты
app.include_router(geocoding.router)
app.include_router(apartment_types.router, prefix="/api")

# Optional: Add health check endpoint with logging
@app.get("/health")
async def health_check():
    structured_logger.debug(
        "Health check requested",
        action="health_check"
    )
    return {"status": "healthy", "service": "geo-api"}
