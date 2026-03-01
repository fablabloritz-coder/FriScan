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
    """Importe des données depuis un fichier JSON (fusion) avec transactions atomiques."""
    
    # 1. Validation taille fichier
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(400, f"Erreur lecture fichier: {str(e)}")
    
    if len(content) > MAX_SIZE:
        raise HTTPException(
            400,
            f"Fichier trop volumineux ({len(content)} > {MAX_SIZE} bytes)"
        )
    
    # 2. Parse et validation JSON
    try:
        data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"JSON invalide: {str(e)}")
    except Exception as e:
        raise HTTPException(400, f"Erreur décodage: {str(e)}")
    
    # 3. Valider schéma (clés recommandées)
    valid_keys = {'products', 'fridge', 'recipes', 'consumption_history', 'weekly_menu', 'shopping_list', 'settings', 'stock_minimums', 'export_date'}
    if not isinstance(data, dict):
        raise HTTPException(400, "Le JSON doit être un objet (dictionnaire)")
    
    unknown_keys = set(data.keys()) - valid_keys
    if unknown_keys:
        raise HTTPException(400, f"Clés inconnues: {', '.join(unknown_keys)}")

    # 4. Import ATOMIQUE (tout ou rien) avec transaction
    db = get_db()
    try:
        # Démarrer transaction IMMÉDIATEMENT
        db.execute("BEGIN IMMEDIATE")
        imported = {}

        # Import produits
        if "products" in data:
            if not isinstance(data["products"], list):
                raise ValueError("'products' doit être une liste")
            for idx, p in enumerate(data["products"]):
                try:
                    db.execute(
                        "INSERT OR IGNORE INTO products (barcode, name, brand, image_url, category, nutrition_json) VALUES (?, ?, ?, ?, ?, ?)",
                        (p.get("barcode"), p.get("name", ""), p.get("brand"), p.get("image_url"), p.get("category"), p.get("nutrition_json", "{}"))
                    )
                except Exception as e:
                    raise ValueError(f"Produit #{idx} invalide: {str(e)}")
            imported["products"] = len(data["products"])

        # Import frigo
        if "fridge" in data:
            if not isinstance(data["fridge"], list):
                raise ValueError("'fridge' doit être une liste")
            for idx, item in enumerate(data["fridge"]):
                try:
                    db.execute(
                        "INSERT INTO fridge_items (name, barcode, image_url, category, quantity, unit, dlc, nutrition_json, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (item.get("name"), item.get("barcode"), item.get("image_url"), item.get("category"),
                         item.get("quantity", 1), item.get("unit", "unité"), item.get("dlc"),
                         item.get("nutrition_json", "{}"), item.get("status", "active"))
                    )
                except Exception as e:
                    raise ValueError(f"Article frigo #{idx} invalide: {str(e)}")
            imported["fridge"] = len(data["fridge"])

        # Import recettes
        if "recipes" in data:
            if not isinstance(data["recipes"], list):
                raise ValueError("'recipes' doit être une liste")
            for idx, r in enumerate(data["recipes"]):
                try:
                    db.execute(
                        "INSERT INTO recipes (title, ingredients_json, instructions, prep_time, cook_time, servings, source_url, image_url, tags_json, diet_tags_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (r.get("title"), r.get("ingredients_json", "[]"), r.get("instructions"),
                         r.get("prep_time", 0), r.get("cook_time", 0), r.get("servings", 4),
                         r.get("source_url"), r.get("image_url"), r.get("tags_json", "[]"), r.get("diet_tags_json", "[]"))
                    )
                except Exception as e:
                    raise ValueError(f"Recette #{idx} invalide: {str(e)}")
            imported["recipes"] = len(data["recipes"])

        # Import settings
        if "settings" in data:
            if not isinstance(data["settings"], list):
                raise ValueError("'settings' doit être une liste")
            for idx, s in enumerate(data["settings"]):
                try:
                    db.execute(
                        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                        (s.get("key"), s.get("value", ""))
                    )
                except Exception as e:
                    raise ValueError(f"Setting #{idx} invalide: {str(e)}")
            imported["settings"] = len(data["settings"])

        # COMMIT si tout réussit
        db.commit()
        return {
            "success": True,
            "imported": imported,
            "message": f"Données importées avec succès. {sum(imported.values())} lignes ajoutées."
        }
    
    except Exception as e:
        # ROLLBACK si erreur!
        try:
            db.rollback()
        except:
            pass
        
        error_msg = str(e)
        import logging
        logging.getLogger("frigoscan").error(f"Import échoué, ROLLBACK: {e}")
        
        raise HTTPException(
            500,
            f"Erreur import: {error_msg}. Aucune donnée n'a été modifiée."
        )
    
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
