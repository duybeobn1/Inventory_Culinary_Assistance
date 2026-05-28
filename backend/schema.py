from pydantic import BaseModel, Field
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


# ==========================================
# Auth Schemas
# ==========================================
class SignUpRequest(BaseModel):
    email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password: str = Field(..., min_length=6)
    display_name: Optional[str] = None


class SignInRequest(BaseModel):
    email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password: str = Field(..., min_length=1)


class AuthResponse(BaseModel):
    status: str
    user_id: str
    email: str
    access_token: str
    display_name: Optional[str] = None


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: dict = {}
    created_at: str


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[dict] = None


# ==========================================
# Ingredient Schemas
# ==========================================
class IngredientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., pattern="^(kg|g|l|ml|unit)$")
    thermal_property: Optional[ThermalProperty] = None
    five_element: Optional[FiveElement] = None
    tastes: Optional[List[str]] = []


class IngredientCreate(IngredientBase):
    pass


class IngredientResponse(IngredientBase):
    id: int
    model_config = {"from_attributes": True}


class InventoryItem(BaseModel):
    ingredient_id: int
    current_quantity: float
    unit: str
    expiry_date: Optional[str] = None
    last_updated: Optional[str] = None


class ReceiptItem(BaseModel):
    name: str
    qty: float = Field(..., gt=0)
    unit: str
    price: float = Field(..., ge=0)
    estimated_shelf_life_days: int = Field(default=5, ge=1)


class ReceiptParseResponse(BaseModel):
    vendor: str
    date: str
    items: List[ReceiptItem]
    total: float = 0.0


class FridgeItemPrediction(BaseModel):
    name: str
    volume_fraction: float = Field(..., ge=0.0, le=1.0)
    box: List[float] = [0.0, 0.0, 0.0, 0.0]


class ConfirmedFridgeItem(BaseModel):
    name: str
    estimated_mass: float
    unit: str = "g"


class MolecularSubstitute(BaseModel):
    ingredient: str
    shared_flavor_compounds: int
    scores: dict
    dietary_compliance: str
    recipe_context: str


class MenuCourse(BaseModel):
    course_type: str
    dish_name: str
    ingredients_used: List[str]
    thermal_property: str
    tcm_reasoning: str


class SaveRecipeRequest(BaseModel):
    recipe_name: str
    recipe_data: dict
    is_favorite: bool = False


class SaveRecipeResponse(BaseModel):
    status: str
    recipe_id: str


class HealthResponse(BaseModel):
    status: str
    version: Optional[str] = None
    message: Optional[str] = None
