from sqlalchemy import Column, Integer, BIGINT, Boolean, DateTime, Text, ForeignKey, text
from geoalchemy2 import Geometry
from sqlalchemy.orm import relationship
from datetime import datetime
from db.db import Base

class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)
    
    tg_bot_id = Column(BIGINT, nullable=True)
    tg_user_id = Column(BIGINT, 
                ForeignKey("public.users.tg_user_id", ondelete="RESTRICT"),
                nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    last_interaction = Column(DateTime, default=datetime.utcnow, nullable=True)
    last_action = Column(Text, nullable=True)  # последнее действие пользователя (опционально)

    

    # Географическая точка — широта/долгота
    location = Column(Geometry(geometry_type='POINT', srid=4326), nullable=True)

    
    is_active = Column(Boolean, nullable=False, server_default=text("true"))

    # Bidirectional relationship
    role = relationship("Role", back_populates="users")

    def __repr__(self):
        return f"<Session(id={self.id}, tg_user_id={self.tg_user_id}, tg_bot_id={self.tg_bot_id}, Location = {self.location})>"
