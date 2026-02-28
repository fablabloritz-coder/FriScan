"""
FriScan — Service de scan de codes-barres
Décode les codes-barres depuis une image uploadée (webcam capture).
"""
import io
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode


def decode_barcode_from_image(image_bytes: bytes) -> str | None:
    """
    Décode un code-barres à partir d'une image en bytes.
    Retourne le code-barres décodé ou None.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Convertir en niveaux de gris pour meilleure détection
        if image.mode != "L":
            image = image.convert("L")

        barcodes = pyzbar_decode(image)

        if barcodes:
            # Retourner le premier code-barres trouvé
            return barcodes[0].data.decode("utf-8")

        return None

    except Exception:
        return None


def decode_barcode_from_text(raw_text: str) -> str | None:
    """
    Nettoie et valide un code-barres saisi manuellement ou via douchette USB.
    Les douchettes USB envoient le code comme frappe clavier.
    """
    cleaned = raw_text.strip()

    # Vérifier que c'est un code-barres valide (chiffres uniquement, 8-14 caractères)
    if cleaned.isdigit() and 8 <= len(cleaned) <= 14:
        return cleaned

    return None
