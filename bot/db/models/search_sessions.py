from sqlalchemy import Column, Integer, ForeignKey, DateTime, func, text
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from db.db import Base


class SearchSession(Base):
    __tablename__ = "search_sessions"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)

    # 🔗 внешний ключ на public.sessions(id)
    session_id = Column(Integer, 
                ForeignKey("public.sessions.id", ondelete="CASCADE"),
                nullable=False)

    user_id = Column(Integer, ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)

    filters = Column(JSONB, nullable=False)                     # JSON с параметрами поиска
    apartment_ids = Column(ARRAY(Integer), nullable=True)      # список ID квартир
    current_index = Column(Integer, nullable=False, default=0, server_default= text("0"))  # текущая позиция пагинации

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Опциональные связи
    user = relationship("User", back_populates="search_sessions")
    session = relationship("Session", back_populates="search_sessions")  
