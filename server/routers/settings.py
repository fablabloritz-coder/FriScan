"""
FrigoScan — Router Réglages.
"""

from fastapi import APIRouter, HTTPException
from server.database import get_db, dict_from_row, rows_to_list, reset_db, backup_db, DEFAULT_SETTINGS
from server.models import SettingUpdate, SettingBulkUpdate, StockMinimum
import json
import random
from datetime import date, timedelta

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


@router.post("/hard-reset")
def hard_reset_database(confirm: bool = False):
    """Supprime TOUT (données utilisateur + réglages) et recrée une base vierge."""
    if not confirm:
        raise HTTPException(400, "Confirmation requise (confirm=true).")
    db = get_db()
    try:
        # Supprimer tout
        db.execute("DELETE FROM fridge_items")
        db.execute("DELETE FROM consumption_history")
        db.execute("DELETE FROM recipes")  # Recettes sauvegardées
        db.execute("DELETE FROM weekly_menu")
        db.execute("DELETE FROM shopping_list")
        db.execute("DELETE FROM banned_recipes")
        db.execute("DELETE FROM stock_minimums")
        # Réinitialiser les réglages aux valeurs par défaut
        db.execute("DELETE FROM settings")
        for key, value in DEFAULT_SETTINGS.items():
            db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        db.commit()
        return {"success": True, "message": "Base de données complètement réinitialisée."}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erreur lors de la réinitialisation : {str(e)}")
    finally:
        db.close()


@router.post("/generate-demo")
def generate_demo_data():
    """Génère une base de démonstration avec données d'exemple."""
    db = get_db()
    try:
        # Données de démo : frigo
        demo_foods = [
            ("Tomate", "fruit-legume"), ("Concombre", "fruit-legume"), ("Ail", "fruit-legume"),
            ("Oignon", "fruit-legume"), ("Carottes", "fruit-legume"), ("Poivron rouge", "fruit-legume"),
            ("Poulet fermier", "viande"), ("Bœuf haché", "viande"), ("Riz basmati", "cereale"),
            ("Pâtes complètes", "cereale"), ("Fromage blanc", "produit-laitier"), ("Lait bio", "produit-laitier"),
            ("Beurre normand", "produit-laitier"), ("Œufs fermiers", "produit-laitier"), ("Huile d'olive", "condiment"),
            ("Vinaigre balsamique", "condiment"), ("Crème fraîche", "produit-laitier"), ("Courgettes", "fruit-legume"),
            ("Aubergine", "fruit-legume"), ("Champignons", "fruit-legume")
        ]
        
        # Ajouter au frigo
        today = date.today()
        for name, category in demo_foods:
            dlc = today + timedelta(days=random.randint(7, 60))
            db.execute(
                "INSERT INTO fridge_items (name, category, quantity, unit, dlc, status) VALUES (?, ?, ?, ?, ?, ?)",
                (name, category, round(random.uniform(1, 5), 1), "unité", dlc.isoformat(), "active")
            )
        
        # Ajouter recettes sauvegardées
        saved_recipes = [
            ("Steak au beurre", json.dumps([{"name": "Steak", "measure": "200g"}, {"name": "Beurre", "measure": "1 c. à soupe"}]),
             "Cuire le steak à feu vif 4 min par côté. Finir avec beurre et persil.", 4, 0, 15),
            ("Pad Thai facile", json.dumps([{"name": "Nouilles de riz", "measure": "200g"}, {"name": "Poulet", "measure": "150g"}, {"name": "Sauce soja", "measure": "2 c. à soupe"}]),
             "Faire sauter le poulet. Ajouter nouilles cuites et sauce. Servir chaud.", 2, 20, 15),
            ("Salade composée Simple", json.dumps([{"name": "Laitue", "measure": "150g"}, {"name": "Tomate", "measure": "2 unités"}]),
             "Mélanger laitue et tomate. Assaisonner avec vinaigrette.", 1, 0, 5),
            ("Omelette du matin Dorée", json.dumps([{"name": "Œufs", "measure": "3 unités"}, {"name": "Fromage", "measure": "50g"}]),
             "Battre les œufs, cuire à la poêle, ajouter fromage à mi-cuisson.", 1, 0, 5),
        ]
        for title, ingredients_json, instructions, servings, prep, cook in saved_recipes:
            db.execute(
                "INSERT OR IGNORE INTO recipes (title, ingredients_json, instructions, servings, prep_time, cook_time) VALUES (?, ?, ?, ?, ?, ?)",
                (title, ingredients_json, instructions, servings, prep, cook)
            )
        
        # Recettes bannies
        banned_recipes = ["Soupe d'algues", "Escargots rôtis", "Tripes gratinées"]
        for title in banned_recipes:
            db.execute(
                "INSERT OR IGNORE INTO banned_recipes (title) VALUES (?)",
                (title,)
            )
        
        # Menu hebdomadaire (7 jours, 2 repas/jour)
        monday = today - timedelta(days=today.weekday())
        meals = [
            ("Omelette du matin", "Petit déj classique avec fromage"),
            ("Salade composée", "Frais et léger"),
            ("Steak au beurre", "Bien cuit avec champignons"),
            ("Pad Thai facile", "Classique asiatique"),
            ("Poulet rôti", "Avec riz et légumes"),
            ("Pâtes bolognaise", "Sauce rouge généreuse"),
        ]
        for day in range(7):
            for meal_idx, meal_type in enumerate(["lunch", "dinner"]):
                recipe_idx = (day * 2 + meal_idx) % len(meals)
                title, notes = meals[recipe_idx]
                week_date = (monday + timedelta(days=day)).isoformat()
                db.execute(
                    "INSERT INTO weekly_menu (week_start, day_of_week, meal_type, recipe_title, notes, servings) VALUES (?, ?, ?, ?, ?, ?)",
                    (monday.isoformat(), day, meal_type, title, notes, 4)
                )
        
        # Réglages : ajouter un régime et une allergie
        db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("diets", json.dumps(["végétarien"]))
        )
        db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("allergens", json.dumps(["arachides", "lactose"]))
        )
        
        db.commit()
        return {
            "success": True,
            "message": "Base de démonstration générée avec succès (frigo, menu, recettes, réglages)!"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erreur lors de la génération de démo : {str(e)}")
    finally:
        db.close()
