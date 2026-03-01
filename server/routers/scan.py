"""
FrigoScan — Router Scan (code-barres).
"""

from fastapi import APIRouter, HTTPException
from server.services.openfoodfacts import lookup_barcode, search_products
from server.database import get_db, dict_from_row
from server.models import ProductCreate
import json

router = APIRouter(prefix="/api/scan", tags=["Scan"])


@router.get("/barcode/{barcode}")
async def scan_barcode(barcode: str):
    """
    Scanne un code-barres :
    1. Cherche d'abord en base locale
    2. Si non trouvé, interroge Open Food Facts
    3. Retourne les infos du produit
    """
    # 1. Recherche locale
    db = get_db()
    try:
        row = db.execute("SELECT * FROM products WHERE barcode = ?", (barcode,)).fetchone()
        if row:
            product = dict_from_row(row)
            product["source"] = "local"
            return {"success": True, "product": product}
    finally:
        db.close()

    # 2. Recherche Open Food Facts
    off_product = await lookup_barcode(barcode)
    if off_product:
        # Sauvegarder en base locale pour le cache
        db = get_db()
        try:
            db.execute(
                """INSERT OR IGNORE INTO products (barcode, name, brand, image_url, category, nutrition_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (off_product["barcode"], off_product["name"], off_product["brand"],
                 off_product["image_url"], off_product["category"], off_product["nutrition_json"])
            )
            db.commit()
            row = db.execute("SELECT * FROM products WHERE barcode = ?", (barcode,)).fetchone()
            product = dict_from_row(row) if row else off_product
        finally:
            db.close()

        product["source"] = "openfoodfacts"
        product["allergens"] = off_product.get("allergens", [])
        return {"success": True, "product": product}

    # 3. Non trouvé
    return {
        "success": False,
        "message": f"Produit avec code-barres {barcode} non trouvé. Vous pouvez l'ajouter manuellement.",
        "barcode": barcode,
    }


@router.get("/search")
async def search_off_products(q: str = ""):
    """Recherche textuelle sur Open Food Facts."""
    if len(q) < 2:
        raise HTTPException(400, "La recherche doit contenir au moins 2 caractères.")
    results = await search_products(q)
    return {"success": True, "products": results[:20]}
