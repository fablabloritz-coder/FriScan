"""
FrigoScan — Router Liste de courses.
"""

from fastapi import APIRouter, HTTPException
from server.database import get_db, dict_from_row, rows_to_list
from server.models import ShoppingItemCreate
import json

router = APIRouter(prefix="/api/shopping", tags=["Liste de courses"])


@router.get("/")
def list_shopping_items(show_purchased: bool = False):
    """Liste les éléments de la liste de courses."""
    db = get_db()
    try:
        if show_purchased:
            rows = db.execute("SELECT * FROM shopping_list ORDER BY is_purchased, category, product_name").fetchall()
        else:
            rows = db.execute("SELECT * FROM shopping_list WHERE is_purchased = 0 ORDER BY category, product_name").fetchall()
        return {"success": True, "items": rows_to_list(rows), "count": len(rows)}
    finally:
        db.close()


@router.post("/")
def add_shopping_item(item: ShoppingItemCreate):
    """Ajoute un article à la liste de courses."""
    db = get_db()
    try:
        # Vérifier si déjà dans la liste
        existing = db.execute(
            "SELECT * FROM shopping_list WHERE LOWER(product_name) = LOWER(?) AND is_purchased = 0",
            (item.product_name,)
        ).fetchone()
        if existing:
            new_qty = existing["quantity"] + item.quantity
            db.execute("UPDATE shopping_list SET quantity = ? WHERE id = ?", (new_qty, existing["id"]))
            db.commit()
            return {"success": True, "message": f"Quantité mise à jour pour '{item.product_name}'."}

        db.execute(
            "INSERT INTO shopping_list (product_name, category, quantity, unit, source) VALUES (?, ?, ?, ?, ?)",
            (item.product_name, item.category, item.quantity, item.unit, item.source)
        )
        db.commit()
        return {"success": True, "message": f"'{item.product_name}' ajouté à la liste."}
    finally:
        db.close()


@router.put("/{item_id}/toggle")
def toggle_purchased(item_id: int):
    """Bascule l'état acheté/non acheté."""
    db = get_db()
    try:
        row = db.execute("SELECT * FROM shopping_list WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Article non trouvé.")
        new_state = 0 if row["is_purchased"] else 1
        db.execute("UPDATE shopping_list SET is_purchased = ? WHERE id = ?", (new_state, item_id))
        db.commit()
        return {"success": True, "is_purchased": bool(new_state)}
    finally:
        db.close()


@router.delete("/{item_id}")
def delete_shopping_item(item_id: int):
    db = get_db()
    try:
        db.execute("DELETE FROM shopping_list WHERE id = ?", (item_id,))
        db.commit()
        return {"success": True, "message": "Article supprimé."}
    finally:
        db.close()


@router.delete("/clear/purchased")
def clear_purchased():
    """Supprime tous les articles achetés."""
    db = get_db()
    try:
        db.execute("DELETE FROM shopping_list WHERE is_purchased = 1")
        db.commit()
        return {"success": True, "message": "Articles achetés supprimés."}
    finally:
        db.close()


@router.delete("/clear/all")
def clear_all():
    """Vide toute la liste de courses."""
    db = get_db()
    try:
        db.execute("DELETE FROM shopping_list")
        db.commit()
        return {"success": True, "message": "Liste de courses vidée."}
    finally:
        db.close()


@router.post("/check-stocks")
def check_stock_alerts():
    """Vérifie les stocks minimum et génère des alertes / ajouts à la liste."""
    db = get_db()
    try:
        minimums = rows_to_list(db.execute("SELECT * FROM stock_minimums").fetchall())
        alerts = []
        for m in minimums:
            current = db.execute(
                "SELECT COALESCE(SUM(quantity), 0) as total FROM fridge_items WHERE LOWER(name) = LOWER(?) AND status='active'",
                (m["product_name"],)
            ).fetchone()["total"]
            if current < m["min_quantity"]:
                # Ajouter à la liste de courses si pas déjà présent
                existing = db.execute(
                    "SELECT id FROM shopping_list WHERE LOWER(product_name) = LOWER(?) AND is_purchased = 0",
                    (m["product_name"],)
                ).fetchone()
                if not existing:
                    db.execute(
                        "INSERT INTO shopping_list (product_name, category, quantity, unit, source) VALUES (?, ?, ?, ?, ?)",
                        (m["product_name"], m["category"], m["min_quantity"] - current, m["unit"], "stock_alert")
                    )
                alerts.append({
                    "product_name": m["product_name"],
                    "current": current,
                    "minimum": m["min_quantity"],
                    "unit": m["unit"],
                })
        db.commit()
        return {"success": True, "alerts": alerts, "count": len(alerts)}
    finally:
        db.close()
