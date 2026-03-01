"""
FrigoScan — Router Réglages.
"""

from fastapi import APIRouter, HTTPException
from server.database import get_db, dict_from_row, rows_to_list, reset_db, backup_db
from server.models import SettingUpdate, SettingBulkUpdate, StockMinimum
import json

router = APIRouter(prefix="/api/settings", tags=["Réglages"])


@router.get("/")
def get_all_settings():
    """Récupère tous les réglages."""
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM settings").fetchall()
        settings = {}
        for row in rows:
            key = row["key"]
            value = row["value"]
            # Essayer de parser JSON
            try:
                settings[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                settings[key] = value
        return {"success": True, "settings": settings}
    finally:
        db.close()


@router.put("/")
def update_setting(update: SettingUpdate):
    """Met à jour un réglage."""
    db = get_db()
    try:
        db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (update.key, update.value)
        )
        db.commit()
        return {"success": True, "message": f"Réglage '{update.key}' mis à jour."}
    finally:
        db.close()


@router.put("/bulk")
def update_settings_bulk(bulk: SettingBulkUpdate):
    """Met à jour plusieurs réglages."""
    db = get_db()
    try:
        for s in bulk.settings:
            db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (s.key, s.value)
            )
        db.commit()
        return {"success": True, "message": f"{len(bulk.settings)} réglage(s) mis à jour."}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Stock minimums
# ---------------------------------------------------------------------------

@router.get("/stock-minimums")
def list_stock_minimums():
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM stock_minimums ORDER BY product_name").fetchall()
        return {"success": True, "minimums": rows_to_list(rows)}
    finally:
        db.close()


@router.post("/stock-minimums")
def add_stock_minimum(item: StockMinimum):
    db = get_db()
    try:
        db.execute(
            "INSERT OR REPLACE INTO stock_minimums (product_name, category, min_quantity, unit) VALUES (?, ?, ?, ?)",
            (item.product_name, item.category, item.min_quantity, item.unit)
        )
        db.commit()
        return {"success": True, "message": f"Stock minimum pour '{item.product_name}' configuré."}
    finally:
        db.close()


@router.delete("/stock-minimums/{item_id}")
def delete_stock_minimum(item_id: int):
    db = get_db()
    try:
        db.execute("DELETE FROM stock_minimums WHERE id = ?", (item_id,))
        db.commit()
        return {"success": True, "message": "Stock minimum supprimé."}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Sauvegarde / Restauration
# ---------------------------------------------------------------------------

@router.post("/backup")
def create_backup():
    """Crée une sauvegarde de la base."""
    try:
        path = backup_db()
        return {"success": True, "path": path, "message": "Sauvegarde créée avec succès."}
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la sauvegarde : {str(e)}")


@router.post("/reset")
def reset_database(confirm: bool = False):
    """Remet la base à zéro (ATTENTION : supprime toutes les données)."""
    if not confirm:
        raise HTTPException(400, "Confirmation requise (confirm=true).")
    try:
        reset_db()
        return {"success": True, "message": "Base de données réinitialisée."}
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la réinitialisation : {str(e)}")
