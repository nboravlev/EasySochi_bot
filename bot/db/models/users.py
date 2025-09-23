from sqlalchemy import Column, Integer, String, ForeignKey, text, DateTime, Boolean, BIGINT, UniqueConstraint
from sqlalchemy.orm import relationship, validates
from datetime import datetime
from db.db import Base
import re

from db.models.roles import Role

class User(Base):
    __tablename__ = "users"
    __table_args__ =  {"schema": "public"}
    

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=True, unique=False)
    firstname = Column(String(50), nullable=True, unique=False)
    phone_number = Column(String(20), nullable=True, unique=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # New columns
    tg_user_id = Column(BIGINT, nullable=False, unique=True)  # Telegram user ID
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    is_bot = Column(Boolean, nullable=False, server_default=text("false"))

    source_id = Column(Integer,
    ForeignKey("public.sources.id", ondelete="SET NULL"),
    nullable=True)

    # Bidirectional relationship
    sessions = relationship("Session",back_populates="user")
    apartments = relationship("Apartment", back_populates = "owner")
    bookings = relationship("Booking", back_populates = "user")
    search_sessions = relationship("SearchSession", back_populates="user")
    booking_chat = relationship("BookingChat", back_populates="user")
    source = relationship("Source", back_populates="users")

    @validates('phone_number')
    def validate_phone_number(self, key, phone_number):
        if phone_number:
            # Remove all non-digit characters for validation
            digits_only = re.sub(r'\D', '', phone_number)
            if len(digits_only) < 10:
                raise ValueError("Номер телефона не короче 10 цифр")
        return phone_number


    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}',tg_user_id={self.tg_user_id})>"
