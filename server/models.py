"""
FrigoScan — Modèles Pydantic pour la validation des données.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, datetime
import re


# ---------------------------------------------------------------------------
# Produits
# ---------------------------------------------------------------------------

class ProductBase(BaseModel):
    barcode: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = None
    category: Optional[str] = Field("autre", max_length=50)
    nutrition_json: Optional[str] = "{}"
    
    @validator('name')
    def validate_name(cls, v):
        v = v.strip()
        if not re.match(r'^[\w\s\-\(\)àâäéèêëïîôöùûüœæçÀÂÄÉÈÊËÏÎÔÖÙÛÜŒÆÇ\.\,]+$', v):
            raise ValueError('Caractères non autorisés dans le nom.')
        return v
    
    @validator('category')
    def validate_category(cls, v):
        if v is None:
            return "autre"
        return v.strip()[:50]


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
    name: str = Field(..., min_length=1, max_length=200)
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = Field("autre", max_length=50)
    quantity: float = Field(1.0, gt=0, le=10000)
    unit: str = Field("unité", max_length=50)
    dlc: Optional[str] = None
    nutrition_json: Optional[str] = "{}"
    
    @validator('name')
    def validate_name(cls, v):
        v = v.strip()
        if not re.match(r'^[\w\s\-\(\)àâäéèêëïîôöùûüœæçÀÂÄÉÈÊËÏÎÔÖÙÛÜŒÆÇ\.\,]+$', v):
            raise ValueError('Caractères non autorisés dans le nom.')
        return v
    
    @validator('dlc')
    def validate_dlc(cls, v):
        if v is None:
            return None
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Format DLC: YYYY-MM-DD requis (ex: 2025-12-31)')
        return v
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantité doit être positive.')
        if v > 10000:
            raise ValueError('Quantité max: 10000.')
        return v


class FridgeItemCreate(FridgeItemBase):
    pass


class FridgeItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = Field(None, max_length=50)
    quantity: Optional[float] = Field(None, gt=0, le=10000)
    unit: Optional[str] = Field(None, max_length=50)
    dlc: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|consumed)$")
    nutrition_json: Optional[str] = None
    image_url: Optional[str] = None
    
    @validator('dlc')
    def validate_dlc(cls, v):
        if v is None:
            return None
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Format DLC: YYYY-MM-DD requis.')
        return v


class FridgeItemOut(FridgeItemBase):
    id: int
    added_at: Optional[str] = None
    status: str = "active"


# ---------------------------------------------------------------------------
# Historique consommation
# ---------------------------------------------------------------------------

class ConsumptionCreate(BaseModel):
    fridge_item_id: Optional[int] = None
    product_name: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = Field(None, max_length=50)
    quantity: float = Field(1.0, gt=0, le=10000)
    unit: str = Field("unité", max_length=50)
    user_name: str = Field("Famille", max_length=100)
    
    @validator('product_name')
    def validate_product_name(cls, v):
        v = v.strip()
        if not re.match(r'^[\w\s\-\(\)àâäéèêëïîôöùûüœæçÀÂÄÉÈÊËÏÎÔÖÙÛÜŒÆÇ\.\,]+$', v):
            raise ValueError('Caractères non autorisés.')
        return v


class ConsumptionOut(ConsumptionCreate):
    id: int
    consumed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Recettes
# ---------------------------------------------------------------------------

class RecipeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    ingredients_json: str = "[]"
    instructions: Optional[str] = Field(None, max_length=10000)
    prep_time: int = Field(0, ge=0, le=1440)  # max 24h en minutes
    cook_time: int = Field(0, ge=0, le=1440)
    servings: int = Field(4, ge=1, le=20)
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    tags_json: str = "[]"
    diet_tags_json: str = "[]"
    
    @validator('title')
    def validate_title(cls, v):
        v = v.strip()
        if not re.match(r'^[\w\s\-\(\)àâäéèêëïîôöùûüœæçÀÂÄÉÈÊËÏÎÔÖÙÛÜŒÆÇ\'\"\.\,]+$', v):
            raise ValueError('Caractères non autorisés dans le titre.')
        return v


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
    meal_type: str = Field("lunch", pattern="^(breakfast|lunch|dinner|snack)$")
    recipe_id: Optional[int] = None
    recipe_title: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=500)
    servings: int = Field(4, ge=1, le=20)


class MenuEntryOut(MenuEntry):
    id: int


# ---------------------------------------------------------------------------
# Liste de courses
# ---------------------------------------------------------------------------

class ShoppingItemBase(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = Field("autre", max_length=50)
    quantity: float = Field(1.0, gt=0, le=10000)
    unit: str = Field("unité", max_length=50)
    source: str = Field("manual", pattern="^(manual|menu|recipe|stock)$")
    
    @validator('product_name')
    def validate_product_name(cls, v):
        v = v.strip()
        if not re.match(r'^[\w\s\-\(\)àâäéèêëïîôöùûüœæçÀÂÄÉÈÊËÏÎÔÖÙÛÜŒÆÇ\.\,]+$', v):
            raise ValueError('Caractères non autorisés.')
        return v


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
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., max_length=10000)
    
    @validator('key')
    def validate_key(cls, v):
        if not re.match(r'^[a-z_]+$', v):
            raise ValueError('Clé invalide.')
        return v


class SettingBulkUpdate(BaseModel):
    settings: list[SettingUpdate]


# ---------------------------------------------------------------------------
# Stock minimum
# ---------------------------------------------------------------------------

class StockMinimum(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = Field("autre", max_length=50)
    min_quantity: float = Field(1.0, gt=0, le=10000)
    unit: str = Field("unité", max_length=50)
    
    @validator('product_name')
    def validate_product_name(cls, v):
        v = v.strip()
        if not re.match(r'^[\w\s\-\(\)àâäéèêëïîôöùûüœæçÀÂÄÉÈÊËÏÎÔÖÙÛÜŒÆÇ\.\,]+$', v):
            raise ValueError('Caractères non autorisés.')
        return v


class StockMinimumOut(StockMinimum):
    id: int

