from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    String,
    Date,
    Numeric,
    CheckConstraint,
    DateTime,Boolean, text, Index, TEXT
)
from sqlalchemy.orm import relationship
from db.db import Base
from datetime import datetime

class BookingChat(Base):
    __tablename__ = "booking_chat"
    __table_args__ =  {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("public.bookings.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)
    message_text = Column(TEXT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

        # Optional: связи
    user = relationship("User", back_populates="booking_chat")
    booking = relationship("Booking", back_populates="booking_chat")


def __repr__(self):
    return f"<booking_id={self.booking_id}, user_id={self.sender_id},message = {self.message_text})>"
