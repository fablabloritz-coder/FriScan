"""
FrigoScan — Router Recettes.
"""

from fastapi import APIRouter, HTTPException, Query
from server.database import get_db, dict_from_row, rows_to_list
from server.models import RecipeCreate
from server.services.recipe_service import (
    search_recipes_online, get_random_recipes, compute_match_score,
    filter_by_diet, suggest_alternatives, load_local_recipes
)
import json

router = APIRouter(prefix="/api/recipes", tags=["Recettes"])


@router.get("/")
def list_recipes():
    """Liste toutes les recettes en base locale."""
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM recipes ORDER BY created_at DESC").fetchall()
        return {"success": True, "recipes": rows_to_list(rows)}
    finally:
        db.close()


@router.get("/suggest")
async def suggest_recipes(
    max_results: int = 10,
    min_score: float = 20.0,
    prefer_dlc: bool = True,
    prefer_seasonal: bool = False,
):
    """
    Suggère des recettes adaptées au contenu du frigo.
    Trie par score de correspondance.
    """
    db = get_db()
    try:
        # Récupérer contenu du frigo
        fridge_rows = db.execute("SELECT * FROM fridge_items WHERE status='active'").fetchall()
        fridge_items = rows_to_list(fridge_rows)

        if not fridge_items:
            return {"success": True, "recipes": [], "message": "Le frigo est vide. Ajoutez des produits pour obtenir des suggestions."}

        # Récupérer réglages
        diets_row = db.execute("SELECT value FROM settings WHERE key='diets'").fetchone()
        allergens_row = db.execute("SELECT value FROM settings WHERE key='allergens'").fetchone()
        diets = json.loads(diets_row["value"]) if diets_row else []
        allergens = json.loads(allergens_row["value"]) if allergens_row else []

        # Exclusions personnalisées
        custom_excl_row = db.execute("SELECT value FROM settings WHERE key='custom_exclusions'").fetchone()
        custom_exclusions = json.loads(custom_excl_row["value"]) if custom_excl_row else []

        # Récupérer recettes locales (base + fichier)
        db_recipes = rows_to_list(db.execute("SELECT * FROM recipes").fetchall())
        local_recipes = load_local_recipes()
        all_recipes = db_recipes + local_recipes

        # Si pas assez de recettes locales, chercher en ligne
        if len(all_recipes) < 20:
            fridge_names = [item["name"] for item in fridge_items[:5]]
            for name in fridge_names[:3]:
                online = await search_recipes_online(name)
                all_recipes.extend(online)

        # Filtrer par régime
        all_recipes = filter_by_diet(all_recipes, diets, allergens, custom_exclusions)

        # Calculer scores
        scored = []
        for recipe in all_recipes:
            ingredients_json = recipe.get("ingredients_json", "[]")
            score, missing = compute_match_score(ingredients_json, fridge_items)
            recipe["match_score"] = score
            recipe["missing_ingredients"] = missing
            if score >= min_score:
                scored.append(recipe)

        # Trier par score décroissant
        scored.sort(key=lambda r: r.get("match_score", 0), reverse=True)

        return {"success": True, "recipes": scored[:max_results]}
    finally:
        db.close()


@router.get("/search")
async def search_recipes(q: str = ""):
    """Recherche de recettes (locale + en ligne)."""
    if len(q) < 2:
        raise HTTPException(400, "Recherche trop courte.")

    db = get_db()
    try:
        # Recherche locale
        local = db.execute(
            "SELECT * FROM recipes WHERE LOWER(title) LIKE ? OR LOWER(ingredients_json) LIKE ?",
            (f"%{q.lower()}%", f"%{q.lower()}%")
        ).fetchall()
        results = rows_to_list(local)

        # Recherche en ligne
        online = await search_recipes_online(q)
        results.extend(online)

        return {"success": True, "recipes": results}
    finally:
        db.close()


@router.post("/")
def add_recipe(recipe: RecipeCreate):
    """Ajoute une recette à la base locale."""
    db = get_db()
    try:
        cursor = db.execute(
            """INSERT INTO recipes (title, ingredients_json, instructions, prep_time, cook_time, servings, source_url, image_url, tags_json, diet_tags_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (recipe.title, recipe.ingredients_json, recipe.instructions,
             recipe.prep_time, recipe.cook_time, recipe.servings,
             recipe.source_url, recipe.image_url, recipe.tags_json, recipe.diet_tags_json)
        )
        db.commit()
        return {"success": True, "id": cursor.lastrowid, "message": f"Recette '{recipe.title}' ajoutée."}
    finally:
        db.close()


@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: int):
    """Supprime une recette."""
    db = get_db()
    try:
        db.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        db.commit()
        return {"success": True, "message": "Recette supprimée."}
    finally:
        db.close()


@router.get("/alternatives/{ingredient}")
def get_alternatives(ingredient: str):
    """Retourne des alternatives pour un ingrédient manquant."""
    alts = suggest_alternatives(ingredient)
    return {"success": True, "ingredient": ingredient, "alternatives": alts}
