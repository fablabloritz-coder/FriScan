"""
FrigoScan — Service produits de saison.
Données pour la France, par mois.
"""

import json
from pathlib import Path
from datetime import datetime

SEASONAL_PATH = Path(__file__).parent.parent / "data" / "seasonal_products.json"


def load_seasonal_data() -> dict:
    """Charge les données de saisonnalité depuis le fichier JSON."""
    if SEASONAL_PATH.exists():
        with open(SEASONAL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_seasonal_products(month: int = None) -> list[dict]:
    """
    Retourne les produits de saison pour le mois donné (1-12).
    Si aucun mois n'est donné, utilise le mois actuel.
    """
    if month is None:
        month = datetime.now().month

    data = load_seasonal_data()
    month_key = str(month)

    products = data.get(month_key, [])
    return products


def is_seasonal(product_name: str, month: int = None) -> bool:
    """Vérifie si un produit est de saison."""
    if month is None:
        month = datetime.now().month

    seasonal = get_seasonal_products(month)
    product_lower = product_name.lower()
    for p in seasonal:
        if p.get("name", "").lower() in product_lower or product_lower in p.get("name", "").lower():
            return True
    return False
