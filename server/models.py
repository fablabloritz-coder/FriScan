"""
FriScan — Modèles de données (SQLAlchemy + Pydantic)
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Float, Date, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, Field

from server.database import Base


# ──────────────────────────── SQLAlchemy Models ────────────────────────────


class ProductDB(Base):
    """Produit stocké dans le frigo."""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nutriscore: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    amount: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_in_fridge: Mapped[bool] = mapped_column(default=True)


# ──────────────────────────── Pydantic Schemas ─────────────────────────────


class ProductCreate(BaseModel):
    """Schéma pour créer/ajouter un produit."""
    barcode: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    brand: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    quantity: Optional[str] = None
    nutriscore: Optional[str] = None
    expiry_date: Optional[date] = None
    amount: int = 1
    notes: Optional[str] = None


class ProductUpdate(BaseModel):
    """Schéma pour modifier un produit."""
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    expiry_date: Optional[date] = None
    amount: Optional[int] = None
    is_in_fridge: Optional[bool] = None


class ProductResponse(BaseModel):
    """Schéma de réponse pour un produit."""
    id: int
    barcode: Optional[str] = None
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    quantity: Optional[str] = None
    nutriscore: Optional[str] = None
    expiry_date: Optional[date] = None
    amount: int
    notes: Optional[str] = None
    added_at: datetime
    is_in_fridge: bool
    days_until_expiry: Optional[int] = None

    model_config = {"from_attributes": True}


class BarcodeRequest(BaseModel):
    """Schéma pour une requête de scan barcode."""
    barcode: str


class OpenFoodFactsProduct(BaseModel):
    """Produit récupéré depuis Open Food Facts."""
    barcode: str
    name: str = "Produit inconnu"
    brand: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    quantity: Optional[str] = None
    nutriscore: Optional[str] = None


class RecipeSuggestion(BaseModel):
    """Suggestion de recette."""
    name: str
    ingredients: list[str]
    matched_ingredients: list[str]
    missing_ingredients: list[str]
    match_score: float = Field(..., ge=0.0, le=1.0)
    instructions: str
    prep_time: Optional[str] = None
    servings: Optional[int] = None
    image_url: Optional[str] = None
    diet_tags: list[str] = []
