"""
FrigoScan — Router Export / Import.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from server.database import get_db, rows_to_list, DB_PATH, init_db
import json
import csv
import io
import shutil
from datetime import datetime
from pathlib import Path

router = APIRouter(prefix="/api/export", tags=["Export/Import"])


@router.get("/fridge/csv")
def export_fridge_csv():
    """Exporte le contenu du frigo en CSV."""
    db = get_db()
    try:
        rows = rows_to_list(db.execute("SELECT * FROM fridge_items WHERE status='active'").fetchall())
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        content = output.getvalue()
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=frigoscan_frigo_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    finally:
        db.close()


@router.get("/fridge/json")
def export_fridge_json():
    """Exporte le contenu du frigo en JSON."""
    db = get_db()
    try:
        rows = rows_to_list(db.execute("SELECT * FROM fridge_items WHERE status='active'").fetchall())
        content = json.dumps(rows, ensure_ascii=False, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=frigoscan_frigo_{datetime.now().strftime('%Y%m%d')}.json"}
        )
    finally:
        db.close()


@router.get("/stats/csv")
def export_stats_csv():
    """Exporte l'historique de consommation en CSV."""
    db = get_db()
    try:
        rows = rows_to_list(db.execute("SELECT * FROM consumption_history ORDER BY consumed_at DESC").fetchall())
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        content = output.getvalue()
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=frigoscan_historique_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    finally:
        db.close()


@router.get("/recipes/json")
def export_recipes_json():
    """Exporte les recettes en JSON."""
    db = get_db()
    try:
        rows = rows_to_list(db.execute("SELECT * FROM recipes").fetchall())
        content = json.dumps(rows, ensure_ascii=False, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=frigoscan_recettes_{datetime.now().strftime('%Y%m%d')}.json"}
        )
    finally:
        db.close()


@router.get("/all/json")
def export_all_json():
    """Exporte toutes les données en JSON."""
    db = get_db()
    try:
        data = {
            "export_date": datetime.now().isoformat(),
            "fridge": rows_to_list(db.execute("SELECT * FROM fridge_items").fetchall()),
            "products": rows_to_list(db.execute("SELECT * FROM products").fetchall()),
            "recipes": rows_to_list(db.execute("SELECT * FROM recipes").fetchall()),
            "consumption_history": rows_to_list(db.execute("SELECT * FROM consumption_history").fetchall()),
            "weekly_menu": rows_to_list(db.execute("SELECT * FROM weekly_menu").fetchall()),
            "shopping_list": rows_to_list(db.execute("SELECT * FROM shopping_list").fetchall()),
            "settings": rows_to_list(db.execute("SELECT * FROM settings").fetchall()),
            "stock_minimums": rows_to_list(db.execute("SELECT * FROM stock_minimums").fetchall()),
        }
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=frigoscan_backup_{datetime.now().strftime('%Y%m%d')}.json"}
        )
    finally:
        db.close()


@router.post("/import/json")
async def import_all_json(file: UploadFile = File(...)):
    """Importe des données depuis un fichier JSON (fusion)."""
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
    except Exception as e:
        raise HTTPException(400, f"Fichier JSON invalide : {str(e)}")

    db = get_db()
    try:
        imported = {}

        # Import produits
        if "products" in data:
            for p in data["products"]:
                db.execute(
                    "INSERT OR IGNORE INTO products (barcode, name, brand, image_url, category, nutrition_json) VALUES (?, ?, ?, ?, ?, ?)",
                    (p.get("barcode"), p.get("name", ""), p.get("brand"), p.get("image_url"), p.get("category"), p.get("nutrition_json", "{}"))
                )
            imported["products"] = len(data["products"])

        # Import frigo
        if "fridge" in data:
            for item in data["fridge"]:
                db.execute(
                    "INSERT INTO fridge_items (name, barcode, image_url, category, quantity, unit, dlc, nutrition_json, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (item.get("name"), item.get("barcode"), item.get("image_url"), item.get("category"),
                     item.get("quantity", 1), item.get("unit", "unité"), item.get("dlc"),
                     item.get("nutrition_json", "{}"), item.get("status", "active"))
                )
            imported["fridge"] = len(data["fridge"])

        # Import recettes
        if "recipes" in data:
            for r in data["recipes"]:
                db.execute(
                    "INSERT INTO recipes (title, ingredients_json, instructions, prep_time, cook_time, servings, source_url, image_url, tags_json, diet_tags_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (r.get("title"), r.get("ingredients_json", "[]"), r.get("instructions"),
                     r.get("prep_time", 0), r.get("cook_time", 0), r.get("servings", 4),
                     r.get("source_url"), r.get("image_url"), r.get("tags_json", "[]"), r.get("diet_tags_json", "[]"))
                )
            imported["recipes"] = len(data["recipes"])

        # Import settings
        if "settings" in data:
            for s in data["settings"]:
                db.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (s.get("key"), s.get("value", ""))
                )
            imported["settings"] = len(data["settings"])

        db.commit()
        return {"success": True, "imported": imported, "message": "Données importées avec succès."}
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de l'import : {str(e)}")
    finally:
        db.close()


@router.get("/database/backup")
def download_database():
    """Télécharge la base de données SQLite complète."""
    if not DB_PATH.exists():
        raise HTTPException(404, "Base de données non trouvée.")
    return StreamingResponse(
        open(str(DB_PATH), "rb"),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=frigoscan_{datetime.now().strftime('%Y%m%d')}.db"}
    )
