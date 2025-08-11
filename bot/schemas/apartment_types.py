# schemas/apartment_type.py
from pydantic import BaseModel

class ApartmentTypeOut(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
