from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.db import Base

class ApartmentType(Base):
    __tablename__ = "apartment_types"
    __table_args__ = {"schema": "apartments"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    
    # Bidirectional relationship
    apartment = relationship("Apartment", back_populates="apartment_type")
    
 