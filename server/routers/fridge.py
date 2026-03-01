"""
FrigoScan — Router Frigo (gestion du contenu du réfrigérateur).
"""

from fastapi import APIRouter, HTTPException, Query
from server.database import get_db, dict_from_row, rows_to_list
from server.models import FridgeItemCreate, FridgeItemUpdate, ConsumptionCreate
from datetime import datetime, date, timedelta
import json

router = APIRouter(prefix="/api/fridge", tags=["Frigo"])


@router.get("/")
def list_fridge_items(
    status: str = "active",
    category: str = None,
    sort: str = "added_at",
    filter_dlc: str = None,
):
    """
    Liste le contenu du frigo.
    filter_dlc: 'soon' (DLC < 3 jours), 'expired' (DLC dépassée), None (tout)
    """
    db = get_db()
    try:
        query = "SELECT * FROM fridge_items WHERE status = ?"
        params = [status]

        if category:
            query += " AND category = ?"
            params.append(category)

        if filter_dlc == "soon":
            soon = (date.today() + timedelta(days=3)).isoformat()
            query += " AND dlc IS NOT NULL AND dlc <= ? AND dlc >= ?"
            params.extend([soon, date.today().isoformat()])
        elif filter_dlc == "expired":
            query += " AND dlc IS NOT NULL AND dlc < ?"
            params.append(date.today().isoformat())

        sort_map = {
            "added_at": "added_at DESC",
            "dlc": "CASE WHEN dlc IS NULL THEN 1 ELSE 0 END, dlc ASC",
            "name": "name ASC",
            "category": "category ASC",
        }
        query += f" ORDER BY {sort_map.get(sort, 'added_at DESC')}"

        rows = db.execute(query, params).fetchall()
        items = rows_to_list(rows)

        # Enrichir avec statut DLC
        today = date.today()
        for item in items:
            raw_dlc = item.get("dlc")
            if raw_dlc:
                try:
                    dlc_date = raw_dlc if isinstance(raw_dlc, date) else date.fromisoformat(str(raw_dlc))
                    delta = (dlc_date - today).days
                    if delta < 0:
                        item["dlc_status"] = "expired"
                    elif delta <= 3:
                        item["dlc_status"] = "soon"
                    else:
                        item["dlc_status"] = "ok"
                    item["dlc_days_left"] = delta
                    item["dlc"] = dlc_date.isoformat()
                except (ValueError, TypeError):
                    item["dlc_status"] = "unknown"
            else:
                item["dlc_status"] = "none"

        return {"success": True, "items": items, "count": len(items)}
    finally:
        db.close()


@router.post("/")
def add_fridge_item(item: FridgeItemCreate):
    """Ajoute un produit au frigo."""
    db = get_db()
    try:
        cursor = db.execute(
            """INSERT INTO fridge_items (product_id, name, barcode, image_url, category, quantity, unit, dlc, nutrition_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.product_id, item.name, item.barcode, item.image_url,
             item.category, item.quantity, item.unit, item.dlc, item.nutrition_json)
        )
        db.commit()
        new_id = cursor.lastrowid
        row = db.execute("SELECT * FROM fridge_items WHERE id = ?", (new_id,)).fetchone()
        return {"success": True, "item": dict_from_row(row), "message": f"'{item.name}' ajouté au frigo."}
    finally:
        db.close()


@router.post("/batch")
def add_fridge_items_batch(items: list[FridgeItemCreate]):
    """Ajoute plusieurs produits au frigo (panier temporaire → frigo)."""
    db = get_db()
    added = []
    try:
        for item in items:
            cursor = db.execute(
                """INSERT INTO fridge_items (product_id, name, barcode, image_url, category, quantity, unit, dlc, nutrition_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item.product_id, item.name, item.barcode, item.image_url,
                 item.category, item.quantity, item.unit, item.dlc, item.nutrition_json)
            )
            added.append({"id": cursor.lastrowid, "name": item.name})
        db.commit()
        return {"success": True, "added": added, "count": len(added), "message": f"{len(added)} produit(s) ajouté(s) au frigo."}
    finally:
        db.close()


@router.put("/{item_id}")
def update_fridge_item(item_id: int, update: FridgeItemUpdate):
    """Met à jour un produit du frigo."""
    db = get_db()
    try:
        existing = db.execute("SELECT * FROM fridge_items WHERE id = ?", (item_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Produit non trouvé dans le frigo.")

        fields = []
        values = []
        update_data = update.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            if val is not None:
                fields.append(f"{key} = ?")
                values.append(val)

        if fields:
            values.append(item_id)
            db.execute(f"UPDATE fridge_items SET {', '.join(fields)} WHERE id = ?", values)
            db.commit()

        row = db.execute("SELECT * FROM fridge_items WHERE id = ?", (item_id,)).fetchone()
        return {"success": True, "item": dict_from_row(row)}
    finally:
        db.close()


@router.delete("/{item_id}")
def delete_fridge_item(item_id: int):
    """Supprime un produit du frigo."""
    db = get_db()
    try:
        existing = db.execute("SELECT * FROM fridge_items WHERE id = ?", (item_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Produit non trouvé.")
        db.execute("DELETE FROM fridge_items WHERE id = ?", (item_id,))
        db.commit()
        return {"success": True, "message": "Produit supprimé."}
    finally:
        db.close()


@router.post("/{item_id}/consume")
def consume_fridge_item(item_id: int, user_name: str = "Famille"):
    """Marque un produit comme consommé et l'ajoute à l'historique."""
    db = get_db()
    try:
        row = db.execute("SELECT * FROM fridge_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Produit non trouvé.")
        item = dict_from_row(row)

        # Ajouter à l'historique
        db.execute(
            """INSERT INTO consumption_history (fridge_item_id, product_name, category, quantity, unit, user_name)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (item_id, item["name"], item["category"], item["quantity"], item["unit"], user_name)
        )
        # Marquer comme consommé
        db.execute("UPDATE fridge_items SET status = 'consumed' WHERE id = ?", (item_id,))
        db.commit()

        # Vérifier stock minimum
        alert = _check_stock_alert(db, item["name"])
        return {"success": True, "message": f"'{item['name']}' marqué comme consommé.", "stock_alert": alert}
    finally:
        db.close()


@router.post("/{item_id}/extend-dlc")
def extend_dlc(item_id: int, days: int = 3):
    """Prolonge la DLC d'un produit."""
    db = get_db()
    try:
        row = db.execute("SELECT * FROM fridge_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Produit non trouvé.")
        current_dlc = row["dlc"]
        if current_dlc:
            dlc_obj = current_dlc if isinstance(current_dlc, date) else date.fromisoformat(str(current_dlc))
            new_dlc = (dlc_obj + timedelta(days=days)).isoformat()
        else:
            new_dlc = (date.today() + timedelta(days=days)).isoformat()
        db.execute("UPDATE fridge_items SET dlc = ? WHERE id = ?", (new_dlc, item_id))
        db.commit()
        return {"success": True, "new_dlc": new_dlc, "message": f"DLC prolongée de {days} jours."}
    finally:
        db.close()


@router.delete("/clear/all")
def clear_fridge(confirm: bool = False):
    """Vide le frigo (avec confirmation)."""
    if not confirm:
        raise HTTPException(400, "Confirmation requise (confirm=true).")
    db = get_db()
    try:
        db.execute("UPDATE fridge_items SET status = 'removed' WHERE status = 'active'")
        db.commit()
        return {"success": True, "message": "Frigo vidé avec succès."}
    finally:
        db.close()


@router.get("/stats/summary")
def fridge_summary():
    """Résumé rapide du frigo."""
    db = get_db()
    try:
        total = db.execute("SELECT COUNT(*) as c FROM fridge_items WHERE status='active'").fetchone()["c"]
        today = date.today().isoformat()
        soon = (date.today() + timedelta(days=3)).isoformat()
        expiring = db.execute(
            "SELECT COUNT(*) as c FROM fridge_items WHERE status='active' AND dlc IS NOT NULL AND dlc <= ? AND dlc >= ?",
            (soon, today)
        ).fetchone()["c"]
        expired = db.execute(
            "SELECT COUNT(*) as c FROM fridge_items WHERE status='active' AND dlc IS NOT NULL AND dlc < ?",
            (today,)
        ).fetchone()["c"]
        categories = db.execute(
            "SELECT category, COUNT(*) as c FROM fridge_items WHERE status='active' GROUP BY category ORDER BY c DESC"
        ).fetchall()
        return {
            "success": True,
            "total": total,
            "expiring_soon": expiring,
            "expired": expired,
            "categories": rows_to_list(categories),
        }
    finally:
        db.close()


def _check_stock_alert(db, product_name: str) -> dict | None:
    """Vérifie si le stock est bas pour un produit donné."""
    min_row = db.execute(
        "SELECT * FROM stock_minimums WHERE LOWER(product_name) = LOWER(?)", (product_name,)
    ).fetchone()
    if not min_row:
        return None
    current = db.execute(
        "SELECT COALESCE(SUM(quantity), 0) as total FROM fridge_items WHERE LOWER(name) = LOWER(?) AND status = 'active'",
        (product_name,)
    ).fetchone()["total"]
    if current < min_row["min_quantity"]:
        return {
            "product_name": product_name,
            "current": current,
            "minimum": min_row["min_quantity"],
            "message": f"Stock bas : {product_name} ({current}/{min_row['min_quantity']} {min_row['unit']})"
        }
    return None
