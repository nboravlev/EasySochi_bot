from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    String,
    Date,
    Numeric,
    CheckConstraint,
    DateTime,Boolean, text, Index, TEXT,
    BIGINT
)
from sqlalchemy.orm import relationship
from db.db import Base
from datetime import datetime

class BookingChat(Base):
    __tablename__ = "booking_chat"
    __table_args__ =  {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("public.bookings.id", ondelete="CASCADE"), nullable=False)
    sender_tg_id = Column(BIGINT, 
                    ForeignKey("public.users.tg_user_id", ondelete="CASCADE"),
                    nullable = False, unique = False)
    message_text = Column(TEXT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

        # Optional: связи
    user = relationship("User", back_populates="booking_chat")
    booking = relationship("Booking", back_populates="booking_chat")


    def __repr__(self):
        return f"<BookingChat(booking_id={self.booking_id}, user_id={self.sender_tg_id},message = {self.message_text})>"
