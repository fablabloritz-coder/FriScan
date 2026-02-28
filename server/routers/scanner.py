"""
FriScan — Router Scanner
Endpoints pour le scan de codes-barres et la recherche Open Food Facts.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException

from server.models import BarcodeRequest, OpenFoodFactsProduct
from server.services.barcode import decode_barcode_from_image, decode_barcode_from_text
from server.services.openfoodfacts import lookup_barcode

router = APIRouter(prefix="/api/scanner", tags=["Scanner"])


@router.post("/image", response_model=OpenFoodFactsProduct | None)
async def scan_barcode_image(file: UploadFile = File(...)):
    """
    Reçoit une image (capture webcam) et décode le code-barres.
    Recherche ensuite le produit sur Open Food Facts.
    """
    contents = await file.read()

    barcode = decode_barcode_from_image(contents)
    if not barcode:
        raise HTTPException(
            status_code=422,
            detail="Aucun code-barres détecté dans l'image. Essayez de rapprocher le produit."
        )

    product = await lookup_barcode(barcode)
    if not product:
        # Retourner un produit minimal avec juste le code-barres
        return OpenFoodFactsProduct(
            barcode=barcode,
            name=f"Produit inconnu ({barcode})",
        )

    return product


@router.post("/barcode", response_model=OpenFoodFactsProduct | None)
async def scan_barcode_text(request: BarcodeRequest):
    """
    Reçoit un code-barres saisi manuellement ou via douchette USB.
    Recherche le produit sur Open Food Facts.
    """
    barcode = decode_barcode_from_text(request.barcode)
    if not barcode:
        raise HTTPException(
            status_code=422,
            detail="Code-barres invalide. Doit contenir 8 à 14 chiffres."
        )

    product = await lookup_barcode(barcode)
    if not product:
        return OpenFoodFactsProduct(
            barcode=barcode,
            name=f"Produit inconnu ({barcode})",
        )

    return product


@router.get("/lookup/{barcode}", response_model=OpenFoodFactsProduct | None)
async def lookup_product(barcode: str):
    """
    Recherche directe d'un produit par code-barres sur Open Food Facts.
    """
    product = await lookup_barcode(barcode)
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Produit avec code-barres {barcode} non trouvé sur Open Food Facts."
        )
    return product
