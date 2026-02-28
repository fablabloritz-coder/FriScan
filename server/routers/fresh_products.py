"""
FriScan — Router Produits Frais (base locale)
Référentiel de produits courants sans code-barres avec durées de conservation.
"""
import json
import os
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/fresh", tags=["Produits frais"])

FRESH_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fresh_products.json")


class FreshProduct(BaseModel):
    name: str
    category: str
    default_expiry_days: int
    icon: str
    keywords: list[str]


def _load_fresh_db() -> list[dict]:
    try:
        with open(FRESH_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


@router.get("/", response_model=list[FreshProduct])
def list_fresh_products(
    search: Optional[str] = Query(None, description="Recherche par nom ou mot-clé"),
    category: Optional[str] = Query(None, description="Filtrer par catégorie"),
):
    """
    Liste les produits frais du référentiel local.
    Permet la recherche par nom/mot-clé et le filtrage par catégorie.
    """
    products = _load_fresh_db()

    if category:
        cat_lower = category.lower()
        products = [p for p in products if p["category"].lower() == cat_lower]

    if search:
        s = search.lower()
        products = [
            p for p in products
            if s in p["name"].lower()
            or any(s in kw.lower() for kw in p.get("keywords", []))
        ]

    return products


@router.get("/categories")
def list_categories():
    """Liste toutes les catégories de produits frais."""
    products = _load_fresh_db()
    categories = sorted(set(p["category"] for p in products))
    return {"categories": categories}


@router.get("/search/{query}", response_model=list[FreshProduct])
def search_fresh_products(query: str):
    """
    Recherche rapide dans le référentiel (autocomplétion).
    Retourne les produits dont le nom ou les mots-clés contiennent la requête.
    """
    products = _load_fresh_db()
    q = query.lower().strip()

    if not q:
        return products[:10]

    results = []
    for p in products:
        # Score de pertinence
        name_lower = p["name"].lower()
        if name_lower.startswith(q):
            results.append((0, p))  # Meilleur match : commence par
        elif q in name_lower:
            results.append((1, p))  # Bon match : contient
        elif any(q in kw.lower() for kw in p.get("keywords", [])):
            results.append((2, p))  # Match dans les mots-clés

    results.sort(key=lambda x: x[0])
    return [p for _, p in results][:15]
