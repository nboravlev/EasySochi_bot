from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    String,
    Date,
    Numeric,
    CheckConstraint,
    DateTime,Boolean, text
)
from sqlalchemy.orm import relationship
from db.db import Base
from datetime import datetime


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        
        CheckConstraint("guest_count > 0", name="check_guest_count_positive"),
        CheckConstraint("start_date < end_date", name="check_dates_order"),
        CheckConstraint("total_price >= 0", name="check_total_price_non_negative"),
        {"schema": "public"}
    )

    id = Column(Integer, primary_key=True)
    
    user_id = Column(Integer, ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)
    apartment_id = Column(Integer, ForeignKey("apartments.apartments.id", ondelete="CASCADE"), nullable=False)
    status_id = Column(Integer, ForeignKey("public.booking_types.id", ondelete="CASCADE"), nullable=False)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    guest_count = Column(Integer, nullable=False)
    
    # total_price может быть вычислена на уровне приложения, но сохраняется в БД
    total_price = Column(Numeric(8, 2), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    comments = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    # Optional: связи
    user = relationship("User", back_populates="booking")
    apartment = relationship("Apartment", back_populates="booking")
    booking_type = relationship("BookingType", back_populates="booking")

def __repr__(self):
    return f"<Apartment_id={self.id}, address={self.address}, user_id={self.user_id},status = {self.stutus_id})>"

