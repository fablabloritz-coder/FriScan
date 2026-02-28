"""
FriScan — Client Open Food Facts
Recherche de produits par code-barres via l'API publique.
"""
import httpx
from server.models import OpenFoodFactsProduct


OFF_API_URL = "https://world.openfoodfacts.org/api/v2/product"


async def lookup_barcode(barcode: str) -> OpenFoodFactsProduct | None:
    """
    Recherche un produit sur Open Food Facts à partir de son code-barres.
    Retourne None si le produit n'est pas trouvé.
    """
    url = f"{OFF_API_URL}/{barcode}.json"
    headers = {
        "User-Agent": "FriScan/1.0 (https://github.com/friscan)"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code != 200:
                return None

            data = response.json()

            if data.get("status") != 1:
                return None

            product = data.get("product", {})

            return OpenFoodFactsProduct(
                barcode=barcode,
                name=product.get("product_name", "Produit inconnu") or "Produit inconnu",
                brand=product.get("brands"),
                category=_extract_main_category(product.get("categories", "")),
                image_url=product.get("image_front_small_url"),
                quantity=product.get("quantity"),
                nutriscore=product.get("nutriscore_grade"),
            )

    except (httpx.RequestError, httpx.TimeoutException, Exception):
        return None


def _extract_main_category(categories_str: str) -> str | None:
    """Extrait la catégorie principale (première) de la chaîne de catégories."""
    if not categories_str:
        return None
    cats = [c.strip() for c in categories_str.split(",")]
    # Prendre la dernière catégorie (souvent la plus spécifique)
    return cats[-1] if cats else None
