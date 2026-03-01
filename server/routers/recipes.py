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
import random as rnd

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

        # Recettes bannies
        banned_rows = db.execute("SELECT LOWER(title) as title FROM banned_recipes").fetchall()
        banned_titles = set(r["title"] for r in banned_rows)

        # Récupérer recettes locales (base + fichier)
        db_recipes = rows_to_list(db.execute("SELECT * FROM recipes").fetchall())
        local_recipes = load_local_recipes()
        all_recipes = db_recipes + local_recipes

        # Si pas assez de recettes locales, chercher en ligne
        if len(all_recipes) < 20:
            fridge_names = [item["name"] for item in fridge_items[:8]]
            rnd.shuffle(fridge_names)
            for name in fridge_names[:4]:
                online = await search_recipes_online(name)
                all_recipes.extend(online)
            # Ajouter quelques recettes aléatoires pour diversité
            extra_random = await get_random_recipes(8)
            all_recipes.extend(extra_random)

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

        # Filtrer les recettes bannies
        scored = [r for r in scored if r.get("title", "").lower().strip() not in banned_titles]

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
        # Recettes bannies
        banned_rows = db.execute("SELECT LOWER(title) as title FROM banned_recipes").fetchall()
        banned_titles = set(r["title"] for r in banned_rows)

        # Recherche locale
        local = db.execute(
            "SELECT * FROM recipes WHERE LOWER(title) LIKE ? OR LOWER(ingredients_json) LIKE ?",
            (f"%{q.lower()}%", f"%{q.lower()}%")
        ).fetchall()
        results = rows_to_list(local)

        # Recherche en ligne
        online = await search_recipes_online(q)
        results.extend(online)

        # Filtrer les bannies
        results = [r for r in results if r.get("title", "").lower().strip() not in banned_titles]

        return {"success": True, "recipes": results}
    finally:
        db.close()


@router.get("/suggest/random")
async def suggest_random_recipes(max_results: int = 12):
    """
    Suggestions de recettes de zéro (aléatoires, filtrées par régime).
    Ignore le contenu du frigo.
    """
    import random as rnd
    db = get_db()
    try:
        # Réglages
        diets_row = db.execute("SELECT value FROM settings WHERE key='diets'").fetchone()
        allergens_row = db.execute("SELECT value FROM settings WHERE key='allergens'").fetchone()
        diets = json.loads(diets_row["value"]) if diets_row else []
        allergens = json.loads(allergens_row["value"]) if allergens_row else []

        custom_excl_row = db.execute("SELECT value FROM settings WHERE key='custom_exclusions'").fetchone()
        custom_exclusions = json.loads(custom_excl_row["value"]) if custom_excl_row else []

        # Recettes bannies
        banned_rows = db.execute("SELECT LOWER(title) as title FROM banned_recipes").fetchall()
        banned_titles = set(r["title"] for r in banned_rows)

        # Récupérer des recettes aléatoires en ligne
        all_recipes = await get_random_recipes(20)

        # Ajouter de la variété avec des termes de recherche
        variety_terms = [
            "chicken", "pasta", "salad", "soup", "beef", "fish", "rice",
            "dessert", "cake", "curry", "stew", "pie", "sandwich", "taco",
            "pizza", "sushi", "noodle", "bread", "seafood", "vegetable",
            "chocolate", "pancake", "grill", "roast", "wrap",
        ]
        rnd.shuffle(variety_terms)
        for term in variety_terms[:3]:
            online = await search_recipes_online(term)
            all_recipes.extend(online)

        # Filtrer par régime
        all_recipes = filter_by_diet(all_recipes, diets, allergens, custom_exclusions)

        # Dédupliquer + filtrer bannies
        seen = set()
        unique = []
        for r in all_recipes:
            title = r.get("title", "").lower().strip()
            if title and title not in seen and title not in banned_titles:
                seen.add(title)
                unique.append(r)

        rnd.shuffle(unique)
        return {"success": True, "recipes": unique[:max_results]}
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
        # Détacher la recette des menus avant suppression (FK constraint)
        db.execute("UPDATE weekly_menu SET recipe_id = NULL WHERE recipe_id = ?", (recipe_id,))
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


# ---- Recettes bannies ----

@router.get("/banned")
def list_banned():
    """Liste les recettes bannies."""
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM banned_recipes ORDER BY created_at DESC").fetchall()
        return {"success": True, "recipes": rows_to_list(rows)}
    finally:
        db.close()


@router.post("/ban")
def ban_recipe(payload: dict):
    """Bannir une recette par titre."""
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "Titre requis.")
    image_url = payload.get("image_url", "")
    db = get_db()
    try:
        db.execute(
            "INSERT OR IGNORE INTO banned_recipes (title, image_url) VALUES (?, ?)",
            (title, image_url)
        )
        db.commit()
        return {"success": True, "message": f"« {title} » bannie."}
    finally:
        db.close()


@router.delete("/ban/{ban_id}")
def unban_recipe(ban_id: int):
    """Débannir une recette."""
    db = get_db()
    try:
        db.execute("DELETE FROM banned_recipes WHERE id = ?", (ban_id,))
        db.commit()
        return {"success": True, "message": "Recette débannie."}
    finally:
        db.close()
