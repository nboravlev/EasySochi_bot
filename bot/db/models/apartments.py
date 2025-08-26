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
    text,
    BIGINT
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime
from db.db import Base

from decimal import Decimal


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
    owner_tg_id = Column(BIGINT, 
                    ForeignKey("public.users.tg_user_id", ondelete="CASCADE"),
                    nullable = False, unique = False)
    floor = Column(Integer, nullable=True)
    has_elevator = Column(Boolean, nullable=False, default = False, server_default=text("false"))
    has_balcony = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    pets_allowed = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    verified = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    max_guests = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(6, 1), nullable=False)
    reward = Column(Numeric(4, 2), nullable=True, default=Decimal("7.00"), server_default='7.00')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_by = Column(BIGINT, nullable=True, unique=False)

    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    is_draft = Column(Boolean, nullable=False, default=True, server_default=text("true"))  
    # координаты с пространственным индексом
    coordinates = Column(Geometry(geometry_type='POINT', srid=4326), nullable=True)

    # отношения (опционально)
    owner = relationship("User", back_populates="apartment")
    apartment_type = relationship("ApartmentType", back_populates="apartments",lazy = "joined")
    booking = relationship("Booking", back_populates = "apartment")
    images = relationship("Image", back_populates = "apartment", lazy="selectin")

    def __repr__(self):
        return f"<Apartment(id={self.id}, address={self.address}, owner_id={self.owner_tg_id})>"
