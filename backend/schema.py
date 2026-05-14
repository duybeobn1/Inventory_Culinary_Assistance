# schemas.py
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class ThermalProperty(str, Enum):
    yin = "Yin"
    yang = "Yang"
    neutral = "Neutral"

class FiveElement(str, Enum):
    wood = "Wood"
    fire = "Fire"
    earth = "Earth"
    metal = "Metal"
    water = "Water"

class IngredientBase(BaseModel):
    name: str
    quantity: float
    unit: str
    thermal_property: Optional[ThermalProperty] = None
    five_element: Optional[FiveElement] = None
    tastes: Optional[List[str]] = []

class IngredientCreate(IngredientBase):
    pass

class IngredientResponse(IngredientBase):
    id: int

    class Config:
        from_attributes = True