"""
FrigoScan — Router Menu de la semaine.
"""

from fastapi import APIRouter, HTTPException
from server.database import get_db, dict_from_row, rows_to_list
from server.models import MenuEntry
from datetime import date, timedelta, datetime
import json

router = APIRouter(prefix="/api/menus", tags=["Menu semaine"])


def _get_week_start(d: date = None) -> str:
    """Retourne le lundi de la semaine."""
    if d is None:
        d = date.today()
    monday = d - timedelta(days=d.weekday())
    return monday.isoformat()


@router.get("/")
def get_current_menu(week_start: str = None):
    """Récupère le menu de la semaine courante."""
    if week_start is None:
        week_start = _get_week_start()
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM weekly_menu WHERE week_start = ? ORDER BY day_of_week, meal_type",
            (week_start,)
        ).fetchall()
        menu = rows_to_list(rows)
        return {"success": True, "week_start": week_start, "menu": menu}
    finally:
        db.close()


@router.post("/")
def add_menu_entry(entry: MenuEntry):
    """Ajoute une entrée au menu."""
    db = get_db()
    try:
        # Vérifier si une entrée existe déjà pour ce créneau
        existing = db.execute(
            "SELECT id FROM weekly_menu WHERE week_start=? AND day_of_week=? AND meal_type=?",
            (entry.week_start, entry.day_of_week, entry.meal_type)
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE weekly_menu SET recipe_id=?, recipe_title=?, notes=?, servings=? WHERE id=?",
                (entry.recipe_id, entry.recipe_title, entry.notes, entry.servings, existing["id"])
            )
        else:
            db.execute(
                """INSERT INTO weekly_menu (week_start, day_of_week, meal_type, recipe_id, recipe_title, notes, servings)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (entry.week_start, entry.day_of_week, entry.meal_type,
                 entry.recipe_id, entry.recipe_title, entry.notes, entry.servings)
            )
        db.commit()
        return {"success": True, "message": "Menu mis à jour."}
    finally:
        db.close()


@router.post("/generate")
async def generate_menu(week_start: str = None, servings: int = 4):
    """
    Génère automatiquement un menu de la semaine
    basé sur le contenu du frigo et les recettes disponibles.
    """
    if week_start is None:
        week_start = _get_week_start()

    db = get_db()
    try:
        # Récupérer contenu du frigo
        fridge_items = rows_to_list(
            db.execute("SELECT * FROM fridge_items WHERE status='active'").fetchall()
        )

        # Récupérer recettes
        recipes = rows_to_list(
            db.execute("SELECT * FROM recipes").fetchall()
        )

        # Import local recipes
        from server.services.recipe_service import load_local_recipes, compute_match_score, filter_by_diet
        local_recipes = load_local_recipes()
        all_recipes = recipes + local_recipes

        # Récupérer réglages
        diets_row = db.execute("SELECT value FROM settings WHERE key='diets'").fetchone()
        allergens_row = db.execute("SELECT value FROM settings WHERE key='allergens'").fetchone()
        diets = json.loads(diets_row["value"]) if diets_row else []
        allergens = json.loads(allergens_row["value"]) if allergens_row else []

        all_recipes = filter_by_diet(all_recipes, diets, allergens)

        # Scorer les recettes
        for recipe in all_recipes:
            score, missing = compute_match_score(recipe.get("ingredients_json", "[]"), fridge_items)
            recipe["match_score"] = score

        all_recipes.sort(key=lambda r: r.get("match_score", 0), reverse=True)

        # Si pas assez de recettes, chercher en ligne
        if len(all_recipes) < 14:
            from server.services.recipe_service import get_random_recipes
            online = await get_random_recipes(max(0, 14 - len(all_recipes)))
            all_recipes.extend(online)

        # Effacer le menu existant pour cette semaine
        db.execute("DELETE FROM weekly_menu WHERE week_start = ?", (week_start,))

        # Générer le menu : déjeuner + dîner pour 7 jours
        menu = []
        recipe_idx = 0
        meal_types = ["lunch", "dinner"]
        for day in range(7):
            for meal in meal_types:
                recipe = all_recipes[recipe_idx % len(all_recipes)] if all_recipes else None
                if recipe:
                    title = recipe.get("title", "Repas libre")
                    recipe_id = recipe.get("id")
                    db.execute(
                        """INSERT INTO weekly_menu (week_start, day_of_week, meal_type, recipe_id, recipe_title, servings)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (week_start, day, meal, recipe_id, title, servings)
                    )
                    menu.append({"day_of_week": day, "meal_type": meal, "recipe_title": title, "recipe_id": recipe_id})
                    recipe_idx += 1
                else:
                    db.execute(
                        """INSERT INTO weekly_menu (week_start, day_of_week, meal_type, recipe_title, servings)
                           VALUES (?, ?, ?, ?, ?)""",
                        (week_start, day, meal, "Repas libre", servings)
                    )
                    menu.append({"day_of_week": day, "meal_type": meal, "recipe_title": "Repas libre"})

        db.commit()
        return {"success": True, "week_start": week_start, "menu": menu, "message": "Menu généré avec succès."}
    finally:
        db.close()


@router.delete("/{entry_id}")
def delete_menu_entry(entry_id: int):
    db = get_db()
    try:
        db.execute("DELETE FROM weekly_menu WHERE id = ?", (entry_id,))
        db.commit()
        return {"success": True, "message": "Entrée supprimée."}
    finally:
        db.close()


@router.delete("/week/{week_start}")
def clear_week_menu(week_start: str):
    db = get_db()
    try:
        db.execute("DELETE FROM weekly_menu WHERE week_start = ?", (week_start,))
        db.commit()
        return {"success": True, "message": "Menu de la semaine vidé."}
    finally:
        db.close()


@router.get("/shopping-list")
def generate_shopping_from_menu(week_start: str = None):
    """Génère une liste de courses à partir du menu de la semaine."""
    if week_start is None:
        week_start = _get_week_start()

    db = get_db()
    try:
        menu_rows = db.execute(
            "SELECT * FROM weekly_menu WHERE week_start = ?", (week_start,)
        ).fetchall()

        fridge_items = rows_to_list(
            db.execute("SELECT * FROM fridge_items WHERE status='active'").fetchall()
        )
        fridge_names = set(item["name"].lower() for item in fridge_items)

        needed = {}
        for row in menu_rows:
            recipe_id = row["recipe_id"]
            if recipe_id:
                recipe = db.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
                if recipe:
                    try:
                        ingredients = json.loads(recipe["ingredients_json"])
                        for ing in ingredients:
                            name = ing.get("name", "").strip()
                            if name.lower() not in fridge_names:
                                needed[name.lower()] = {"name": name, "measure": ing.get("measure", "")}
                    except Exception:
                        pass

        shopping = list(needed.values())
        return {"success": True, "shopping_list": shopping, "count": len(shopping)}
    finally:
        db.close()
