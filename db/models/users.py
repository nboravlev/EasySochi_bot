from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from db.db import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    phone_number = Column(Integer, nullable=True, unique=True)
    role_id = role_id = Column(Integer, ForeignKey("public.roles.id"), server_default=text("1"))

    role = relationship("Role")
