"""
FrigoScan — Service Open Food Facts.
Recherche de produits par code-barres via l'API Open Food Facts (gratuite).
"""

import httpx
import json
import logging
from typing import Optional

logger = logging.getLogger("frigoscan.openfoodfacts")

OFF_BASE_URL = "https://world.openfoodfacts.org/api/v2/product"
SEARCH_URL = "https://world.openfoodfacts.net/cgi/search.pl"
TIMEOUT = 8.0


async def lookup_barcode(barcode: str) -> Optional[dict]:
    """
    Recherche un produit par code-barres sur Open Food Facts.
    Retourne un dict normalisé ou None si non trouvé.
    """
    url = f"{OFF_BASE_URL}/{barcode}.json"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("status") != 1:
                return None
            product = data.get("product", {})
            return _normalize_product(product, barcode)
    except (httpx.RequestError, httpx.TimeoutException, Exception) as e:
        logger.warning(f"Erreur Open Food Facts pour {barcode}: {e}")
        return None


async def search_products(query: str, page: int = 1, page_size: int = 20) -> list[dict]:
    """Recherche textuelle de produits."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(SEARCH_URL, params={
                "search_terms": query,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page": page,
                "page_size": page_size,
                "lc": "fr",
                "cc": "fr",
            })
            if resp.status_code != 200:
                return []
            data = resp.json()
            products = data.get("products", [])
            return [_normalize_product(p) for p in products if p.get("product_name")]
    except Exception as e:
        logger.warning(f"Erreur recherche OFF: {e}")
        return []


def _normalize_product(product: dict, barcode: str = None) -> dict:
    """Normalise les données OFF vers le format FrigoScan."""
    nutriments = product.get("nutriments", {})
    nutrition = {
        "energy_kcal": nutriments.get("energy-kcal_100g", 0),
        "fat": nutriments.get("fat_100g", 0),
        "saturated_fat": nutriments.get("saturated-fat_100g", 0),
        "carbohydrates": nutriments.get("carbohydrates_100g", 0),
        "sugars": nutriments.get("sugars_100g", 0),
        "fiber": nutriments.get("fiber_100g", 0),
        "proteins": nutriments.get("proteins_100g", 0),
        "salt": nutriments.get("salt_100g", 0),
        "nutriscore": product.get("nutriscore_grade", ""),
    }

    # Détection des allergènes
    allergens_tags = product.get("allergens_tags", [])
    allergens = [a.replace("en:", "") for a in allergens_tags]

    # Catégorie
    categories = product.get("categories_tags", [])
    category = _detect_category(categories, product.get("categories", ""))

    return {
        "barcode": barcode or product.get("code", ""),
        "name": product.get("product_name", product.get("product_name_fr", "Produit inconnu")),
        "brand": product.get("brands", ""),
        "image_url": product.get("image_front_small_url", product.get("image_url", "")),
        "category": category,
        "nutrition_json": json.dumps(nutrition),
        "allergens": allergens,
        "quantity_info": product.get("quantity", ""),
    }


def _detect_category(categories_tags: list, categories_str: str) -> str:
    """Détecte la catégorie principale du produit."""
    cat_map = {
        "fruit": "fruits",
        "legume": "légumes",
        "vegetable": "légumes",
        "viande": "viandes",
        "meat": "viandes",
        "poisson": "poissons",
        "fish": "poissons",
        "lait": "produits laitiers",
        "dairy": "produits laitiers",
        "fromage": "produits laitiers",
        "cheese": "produits laitiers",
        "yogurt": "produits laitiers",
        "yaourt": "produits laitiers",
        "pain": "boulangerie",
        "bread": "boulangerie",
        "boisson": "boissons",
        "beverage": "boissons",
        "drink": "boissons",
        "cereale": "céréales",
        "cereal": "céréales",
        "pâte": "féculents",
        "pasta": "féculents",
        "riz": "féculents",
        "rice": "féculents",
        "conserve": "conserves",
        "canned": "conserves",
        "condiment": "condiments",
        "sauce": "condiments",
        "spice": "épices",
        "epice": "épices",
        "surgelé": "surgelés",
        "frozen": "surgelés",
        "snack": "snacks",
        "biscuit": "snacks",
        "chocolate": "snacks",
        "chocolat": "snacks",
        "oeuf": "oeufs",
        "egg": "oeufs",
        "charcuterie": "charcuterie",
    }
    combined = " ".join(categories_tags + [categories_str]).lower()
    for keyword, cat in cat_map.items():
        if keyword in combined:
            return cat
    return "autre"
