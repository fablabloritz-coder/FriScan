"""
FrigoScan — Router Produits de saison.
"""

from fastapi import APIRouter
from server.services.seasonal_service import get_seasonal_products, is_seasonal

router = APIRouter(prefix="/api/seasonal", tags=["Produits de saison"])


@router.get("/")
def get_current_seasonal(month: int = None):
    """Retourne les produits de saison pour le mois donné (ou courant)."""
    products = get_seasonal_products(month)
    return {"success": True, "products": products, "count": len(products)}


@router.get("/check/{product_name}")
def check_seasonal(product_name: str, month: int = None):
    """Vérifie si un produit est de saison."""
    result = is_seasonal(product_name, month)
    return {"success": True, "product": product_name, "is_seasonal": result}
