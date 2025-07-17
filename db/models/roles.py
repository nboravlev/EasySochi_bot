from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db import Base

class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    users = relationship("User", back_populates="role")
