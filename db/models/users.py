from sqlalchemy import Column, Integer, String, ForeignKey, text, DateTime, Boolean, BIGINT, UniqueConstraint
from sqlalchemy.orm import relationship, validates
from datetime import datetime
from db.db import Base
import re

from db.models.roles import Role

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tg_user_id", "role_id", name="uq_tg_user_role"),
        UniqueConstraint("username", "role_id", name="uq_name_role"),
        UniqueConstraint("phone_number", "role_id", name="uq_phone_role"),
        {"schema": "public"}
    )

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=False)
    phone_number = Column(String(20), nullable=True, unique=False)
    role_id = Column(
        Integer, 
        ForeignKey("public.roles.id", ondelete="SET DEFAULT"), 
        server_default=text("1"),
        nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # New columns
    tg_user_id = Column(BIGINT, nullable=True, unique=False)  # Telegram user ID
    is_active = Column(Boolean, nullable=False, server_default=text("true"))

    # Bidirectional relationship
    role = relationship("Role", back_populates="users")
    sessions = relationship("Session",back_populates="user")
    apartment = relationship("Apartment", back_poulates = "owner")
    booking = relationship("Booking", back_populates = "user")

    @validates('phone_number')
    def validate_phone_number(self, key, phone_number):
        if phone_number:
            # Remove all non-digit characters for validation
            digits_only = re.sub(r'\D', '', phone_number)
            if len(digits_only) < 10:
                raise ValueError("Номер телефона не короче 10 цифр")
        return phone_number

    @validates('username')
    def validate_username(self, key, username):
        if not username or len(username.strip()) < 3:
            raise ValueError("Username минимум 3 символа")
        return username.strip()

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}',tg_user_id={self.tg_user_id})>"
