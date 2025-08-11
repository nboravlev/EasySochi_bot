from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Boolean,
    DateTime,
    String,
    text
)
from db.db import Base
from sqlalchemy.orm import relationship
from datetime import datetime


class Image(Base):
    __tablename__ = "images"
    __table_args__ = {"schema": "media"}

    id = Column(Integer, primary_key=True)

    apartment_id = Column(Integer, ForeignKey("apartments.apartments.id", ondelete="CASCADE"), nullable=False)

    tg_file_id = Column(String, nullable=False)  # идентификатор файла в Telegram
    is_main = Column(Boolean, nullable=False, default=False, server_default=text("false"))  # главное фото
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))  # включено в выдачу

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Optional: связь с Apartment
    apartment = relationship("Apartment", back_populates="images")
