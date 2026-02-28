"""
FriScan — Router Recettes
Suggestions de recettes basées sur le contenu du frigo.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta

from server.database import get_db
from server.models import ProductDB, RecipeSuggestion
from server.services.recipe_engine import suggest_recipes

router = APIRouter(prefix="/api/recipes", tags=["Recettes"])


@router.get("/suggestions", response_model=list[RecipeSuggestion])
def get_recipe_suggestions(
    max_results: int = Query(10, ge=1, le=50),
    min_match: float = Query(0.3, ge=0.0, le=1.0),
    prioritize_expiring: bool = Query(True, description="Prioriser les produits bientôt périmés"),
    expiry_days: int = Query(3, ge=1, le=30, description="Nb jours avant péremption pour alerte"),
    diet: Optional[str] = Query(None, description="Régimes alimentaires (ex: vegetarien,vegan)"),
    db: Session = Depends(get_db),
):
    """
    Génère des suggestions de recettes basées sur les produits actuellement dans le frigo.
    Les recettes utilisant des produits proches de la péremption sont priorisées.
    Filtre optionnel par régime alimentaire.
    """
    # Récupérer tous les produits dans le frigo
    products = db.query(ProductDB).filter(ProductDB.is_in_fridge == True).all()

    if not products:
        return []

    fridge_items = [p.name for p in products]

    # Identifier les produits proches de la péremption (configurable)
    expiring_items = None
    if prioritize_expiring:
        today = date.today()
        expiring_items = [
            p.name for p in products
            if p.expiry_date and (p.expiry_date - today).days <= expiry_days
        ]

    # Parse diet filter
    diet_filter = None
    if diet:
        diet_filter = [d.strip() for d in diet.split(",") if d.strip()]

    return suggest_recipes(
        fridge_products=fridge_items,
        max_results=max_results,
        min_match_ratio=min_match,
        prioritize_expiring=expiring_items,
        diet_filter=diet_filter,
    )
