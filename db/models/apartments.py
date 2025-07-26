from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    CheckConstraint,
    text
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime
from db.db import Base


class Apartment(Base):
    __tablename__ = "apartments"
    __table_args__ = (
        CheckConstraint('max_guests > 0', name='check_max_guests_positive'),
        CheckConstraint('price >= 0', name='check_price_non_negative'),
        {"schema": "apartments"}
    )

    id = Column(Integer, primary_key=True)
    address = Column(String(255), nullable=False)
    short_address = Column(String(100), nullable=False)
    type_id = Column(Integer, ForeignKey("apartments.apartment_types.id", ondelete="RESTRICT"), nullable=False)
    owner_id = Column(Integer, ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)

    floor = Column(Integer, nullable=True)
    has_elevator = Column(Boolean, nullable=False, default = False, server_default=text("false"))
    has_balcony = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    pets_allowed = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    verified = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    max_guests = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(6, 1), nullable=False)
    reward = Column(Integer, nullable=True, default = 7, server_default='7')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    is_draft = Column(Boolean, nullable=False, default=True, server_default=text("true"))  
    # координаты с пространственным индексом
    coordinates = Column(Geometry(geometry_type='POINT', srid=4326), nullable=True)

    # отношения (опционально)
    owner = relationship("User", back_populates="apartment")
    apartment_type = relationship("ApartmentType", back_populates="apartments")
    booking = relationship("Booking", back_populates = "apartment")
    images = relationship("Image", back_populates = "apartment")

    def __repr__(self):
        return f"<Apartment(id={self.id}, address={self.address}, owner_id={self.owner_id})>"
