"""
FrigoScan — Service de recettes Marmiton (API française).
Alternative à TheMealDB avec recettes françaises et européennes.

Utilise une API Marmiton gratuite pour récupérer les recettes.
"""

import httpx
import json
import logging
import re
from typing import Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("frigoscan.marmiton")

# Configuration API Marmiton
# Nota: L'API Marmiton est un web scraper Node.js, nous utilisons l'endpoint public
MARMITON_API_BASE = "https://api.marmiton.org"
MARMITON_API_SEARCH = "https://api.marmiton.org/recipes"  # À adapter selon disponibilité
TIMEOUT = 15.0

# Liste des catégories Marmiton en français
MARMITON_CATEGORIES = [
    "Entrée",
    "Plat",
    "Dessert",
    "Sauce",
    "Petit-déjeuner",
    "Soupe",
    "Salades",
    "Pains",
    "Boissons",
]

# Temps de préparation/cuisson communs
COOKING_TIMES = {
    "rapide": 15,
    "moyen": 30,
    "long": 60,
}


def _normalize_marmiton_recipe(recipe: dict) -> dict:
    """
    Normalise une recette Marmiton au format FrigoScan interne.
    
    Format Marmiton original:
    {
        "title": "Spaghetti Carbonara",
        "url": "...",
        "author": "...",
        "difficulty": "Facile",
        "ingredients": ["1 oeuf", "100g pâtes", ...],
        "steps": ["Cuire les pâtes...", ...],
        "tags": ["Végétarien", "Rapide", ...],
        "servings": 4,
        "prep_time": 15,
        "cook_time": 20
    }
    
    Format FrigoScan:
    {
        "id": hash(title),
        "title": "Spaghetti Carbonara",
        "source": "marmiton",
        "url": "...",
        "difficulty": "easy|medium|hard",
        "ingredients": [...],
        "instructions": "Cuire les pâtes...",
        "tags": [...],
        "servings": 4,
        "prep_time": 15,
        "cook_time": 20,
        "total_time": 35,
        "image_url": "...",
        "italian": False  # Pour tracking
    }
    """
    
    # Générer un ID simple basé sur le titre
    recipe_id = hash(recipe.get("title", "")) % (10 ** 8)
    
    # Normaliser la difficulté
    difficulty_map = {
        "facile": "easy",
        "moyen": "medium",
        "difficile": "hard",
        "easy": "easy",
        "medium": "medium",
        "hard": "hard",
    }
    difficulty = recipe.get("difficulty", "medium").lower()
    difficulty = difficulty_map.get(difficulty, "medium")
    
    # Temps de préparation et cuisson
    prep_time = recipe.get("prep_time", 0) or 0
    cook_time = recipe.get("cook_time", 0) or 0
    total_time = prep_time + cook_time
    
    # Instructions: joindre les steps avec des retours à la ligne
    steps = recipe.get("steps", [])
    if isinstance(steps, list):
        instructions = "<br/>".join(steps) if steps else "Voir le site Marmiton pour les détails."
    else:
        instructions = str(steps)
    
    # Tags (filtrer les vides)
    tags = [t.strip() for t in recipe.get("tags", []) if t and isinstance(t, str)]
    
    # Ingrédients
    ingredients = recipe.get("ingredients", [])
    if ingredients and not isinstance(ingredients, list):
        ingredients = [ingredients]
    
    # JSON ingrédients au format FrigoScan
    ingredients_json = json.dumps([
        {
            "name": ing.strip() if isinstance(ing, str) else str(ing),
            "quantity": 1,
            "unit": ""
        }
        for ing in (ingredients or [])
    ])
    
    return {
        "id": recipe_id,
        "title": recipe.get("title", "Sans titre"),
        "source": "marmiton",
        "url": recipe.get("url", ""),
        "author": recipe.get("author", "Marmiton Community"),
        "difficulty": difficulty,
        "ingredients_json": ingredients_json,
        "instructions": instructions,
        "tags_json": json.dumps(tags),
        "diet_tags_json": json.dumps([]),  # À implémenter si Marmiton le fournit
        "servings": recipe.get("servings", 4),
        "prep_time": prep_time,
        "cook_time": cook_time,
        "total_time": total_time,
        "image_url": recipe.get("image_url", ""),
        "italian": False,
        "created_at": datetime.now().isoformat(),
    }


async def search_marmiton_recipes(query: str, limit: int = 12) -> list[dict]:
    """
    Recherche de recettes sur Marmiton via l'API.
    
    ⚠️ Note: Marmiton API est réservée au Node.js
    Fallback: Utiliser le web scraping ou une API tierce
    """
    
    logger.info(f"🔍 Recherche Marmiton pour: '{query}'")
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Essayer l'API Marmiton publique (si disponible)
            params = {
                "search": query,
                "limit": limit,
                "offset": 0,
            }
            
            # ⚠️ L'API Marmiton officielle nécessite Node.js
            # Nous utilisons une URI générique - adapter si une instance REST est disponible
            resp = await client.get(
                "https://www.marmiton.org/recettes/",
                timeout=TIMEOUT,
                follow_redirects=True
            )
            
            if resp.status_code == 200:
                # Parse la page (web scraping au besoin)
                # Pour l'instant, retourner les résultats locaux de fallback
                logger.warning("⚠️ Marmiton API n'est pas disponible, utilisant recettes locales")
                return _get_fallback_recipes(query)
            else:
                logger.error(f"❌ Marmiton API error: {resp.status_code}")
                return _get_fallback_recipes(query)
    
    except Exception as e:
        logger.error(f"❌ Marmiton search error: {e}")
        return _get_fallback_recipes(query)


def _get_fallback_recipes(query: str) -> list[dict]:
    """
    Recettes de fallback Marmiton-style (chargées depuis JSON).
    Retourne toutes les recettes ou filtrées selon la requête.
    """
    
    # Charger les recettes depuis le fichier JSON
    fallback_file = Path(__file__).parent.parent / "data" / "marmiton_fallback.json"
    
    try:
        if fallback_file.exists():
            with open(fallback_file, 'r', encoding='utf-8') as f:
                fallback_recipes = json.load(f)
            logger.debug(f"📖 Chargé {len(fallback_recipes)} recettes depuis {fallback_file.name}")
        else:
            logger.warning(f"⚠️ Fichier fallback non trouvé: {fallback_file}")
            fallback_recipes = []
    except Exception as e:
        logger.error(f"❌ Erreur chargement fallback: {e}")
        fallback_recipes = []
    
    # Filtrer selon la requête si fournie
    if query:
        query_lower = query.lower()
        matching = [
            r for r in fallback_recipes
            if query_lower in r.get("title", "").lower() or
               any(query_lower in ing.lower() for ing in r.get("ingredients", []))
        ]
        recipes_to_use = matching if matching else fallback_recipes
    else:
        recipes_to_use = fallback_recipes
    
    # Normaliser et retourner
    return [_normalize_marmiton_recipe(r) for r in recipes_to_use]


async def get_random_marmiton_recipes(count: int = 5) -> list[dict]:
    """Récupère des recettes aléatoires Marmiton."""
    
    logger.info(f"🎲 Recettes aléatoires Marmiton x{count}")
    
    try:
        recipes = _get_fallback_recipes("")
        # Mélanger et retourner count recettes aléatoires
        import random
        random.shuffle(recipes)
        return recipes[:count]
    except Exception as e:
        logger.error(f"❌ Random recipes error: {e}")
        return []


def get_marmiton_categories() -> list[str]:
    """Retourne les catégories disponibles sur Marmiton."""
    return MARMITON_CATEGORIES
