"""
FrigoScan — Modèles Pydantic pour la validation des données.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Produits
# ---------------------------------------------------------------------------

class ProductBase(BaseModel):
    barcode: Optional[str] = None
    name: str
    brand: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = "autre"
    nutrition_json: Optional[str] = "{}"


class ProductCreate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: int
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Frigo
# ---------------------------------------------------------------------------

class FridgeItemBase(BaseModel):
    product_id: Optional[int] = None
    name: str
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = "autre"
    quantity: float = 1.0
    unit: str = "unité"
    dlc: Optional[str] = None
    nutrition_json: Optional[str] = "{}"


class FridgeItemCreate(FridgeItemBase):
    pass


class FridgeItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    dlc: Optional[str] = None
    status: Optional[str] = None
    nutrition_json: Optional[str] = None
    image_url: Optional[str] = None


class FridgeItemOut(FridgeItemBase):
    id: int
    added_at: Optional[str] = None
    status: str = "active"


# ---------------------------------------------------------------------------
# Historique consommation
# ---------------------------------------------------------------------------

class ConsumptionCreate(BaseModel):
    fridge_item_id: Optional[int] = None
    product_name: str
    category: Optional[str] = None
    quantity: float = 1.0
    unit: str = "unité"
    user_name: str = "Famille"


class ConsumptionOut(ConsumptionCreate):
    id: int
    consumed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Recettes
# ---------------------------------------------------------------------------

class RecipeBase(BaseModel):
    title: str
    ingredients_json: str = "[]"
    instructions: Optional[str] = None
    prep_time: int = 0
    cook_time: int = 0
    servings: int = 4
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    tags_json: str = "[]"
    diet_tags_json: str = "[]"


class RecipeCreate(RecipeBase):
    pass


class RecipeOut(RecipeBase):
    id: int
    created_at: Optional[str] = None
    match_score: Optional[float] = None
    missing_ingredients: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Menu hebdo
# ---------------------------------------------------------------------------

class MenuEntry(BaseModel):
    week_start: str
    day_of_week: int = Field(ge=0, le=6)
    meal_type: str = "lunch"
    recipe_id: Optional[int] = None
    recipe_title: Optional[str] = None
    notes: Optional[str] = None
    servings: int = 4


class MenuEntryOut(MenuEntry):
    id: int


# ---------------------------------------------------------------------------
# Liste de courses
# ---------------------------------------------------------------------------

class ShoppingItemBase(BaseModel):
    product_name: str
    category: Optional[str] = "autre"
    quantity: float = 1.0
    unit: str = "unité"
    source: str = "manual"


class ShoppingItemCreate(ShoppingItemBase):
    pass


class ShoppingItemOut(ShoppingItemBase):
    id: int
    is_purchased: bool = False
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Réglages
# ---------------------------------------------------------------------------

class SettingUpdate(BaseModel):
    key: str
    value: str


class SettingBulkUpdate(BaseModel):
    settings: list[SettingUpdate]


# ---------------------------------------------------------------------------
# Stock minimum
# ---------------------------------------------------------------------------

class StockMinimum(BaseModel):
    product_name: str
    category: Optional[str] = "autre"
    min_quantity: float = 1.0
    unit: str = "unité"


class StockMinimumOut(StockMinimum):
    id: int
