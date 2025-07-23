from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.db import Base

class BookingType(Base):
    __tablename__ = "booking_types"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    
    # Bidirectional relationship
    booking = relationship("Booking", back_populates="booking_type")
