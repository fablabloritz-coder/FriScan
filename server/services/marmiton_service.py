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
from urllib.parse import quote_plus

logger = logging.getLogger("frigoscan.marmiton")

# Configuration API Marmiton
# Nota: L'API Marmiton est un web scraper Node.js, nous utilisons l'endpoint public
MARMITON_API_BASE = "https://api.marmiton.org"
MARMITON_API_SEARCH = "https://api.marmiton.org/recipes"  # À adapter selon disponibilité
TIMEOUT = 15.0

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

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


def _extract_json_ld_blocks(html: str) -> list[dict]:
    """Extrait les blocs JSON-LD d'une page HTML."""
    blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    parsed: list[dict] = []

    for raw in blocks:
        payload = raw.strip()
        if not payload:
            continue
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                parsed.append(data)
            elif isinstance(data, list):
                parsed.extend([item for item in data if isinstance(item, dict)])
        except Exception:
            continue
    return parsed


def _duration_to_minutes(value: str | None) -> int:
    """Convertit une durée ISO8601 (PT20M, PT1H15M) en minutes."""
    if not value:
        return 0
    match = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?$", value)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    return hours * 60 + minutes


def _extract_itemlist_from_search(html: str, limit: int) -> list[dict]:
    """Extrait les résultats (titre/url/image) depuis ItemList JSON-LD Marmiton."""
    results: list[dict] = []
    for block in _extract_json_ld_blocks(html):
        if block.get("@type") != "ItemList":
            continue
        elements = block.get("itemListElement") or []
        for elem in elements:
            if not isinstance(elem, dict):
                continue
            title = (elem.get("name") or "").strip()
            url = (elem.get("url") or "").strip()
            image = (elem.get("image") or "").strip()
            if not title or not url:
                continue
            results.append({
                "title": title,
                "url": url,
                "image_url": image,
            })
            if len(results) >= limit:
                return results
    return results


async def _enrich_recipe_from_detail(client: httpx.AsyncClient, base_recipe: dict) -> dict:
    """Enrichit un résultat Marmiton via la page détail (JSON-LD Recipe)."""
    detail_url = base_recipe.get("url", "")
    if not detail_url:
        return base_recipe

    try:
        resp = await client.get(detail_url, timeout=TIMEOUT, follow_redirects=True)
        if resp.status_code != 200:
            return base_recipe
        blocks = _extract_json_ld_blocks(resp.text)
        recipe_block = next((b for b in blocks if b.get("@type") == "Recipe"), None)
        if not recipe_block:
            return base_recipe

        ingredients = recipe_block.get("recipeIngredient") or []
        if not isinstance(ingredients, list):
            ingredients = []

        instructions_raw = recipe_block.get("recipeInstructions") or []
        instructions: list[str] = []
        if isinstance(instructions_raw, str):
            instructions = [instructions_raw]
        elif isinstance(instructions_raw, list):
            for step in instructions_raw:
                if isinstance(step, dict):
                    text = (step.get("text") or "").strip()
                    if text:
                        instructions.append(text)
                elif isinstance(step, str) and step.strip():
                    instructions.append(step.strip())

        category = recipe_block.get("recipeCategory")
        keywords = recipe_block.get("keywords")
        tags: list[str] = []
        if isinstance(category, str) and category.strip():
            tags.append(category.strip())
        elif isinstance(category, list):
            tags.extend([c.strip() for c in category if isinstance(c, str) and c.strip()])
        if isinstance(keywords, str):
            tags.extend([k.strip() for k in keywords.split(",") if k.strip()])

        prep_time = _duration_to_minutes(recipe_block.get("prepTime"))
        cook_time = _duration_to_minutes(recipe_block.get("cookTime"))
        if prep_time == 0 and cook_time == 0:
            total = _duration_to_minutes(recipe_block.get("totalTime"))
            prep_time = total // 2
            cook_time = total - prep_time

        image = recipe_block.get("image")
        image_url = base_recipe.get("image_url", "")
        if isinstance(image, str):
            image_url = image
        elif isinstance(image, list) and image:
            first = image[0]
            if isinstance(first, str):
                image_url = first
            elif isinstance(first, dict):
                image_url = first.get("url", image_url)
        elif isinstance(image, dict):
            image_url = image.get("url", image_url)

        servings = recipe_block.get("recipeYield", 4)
        if isinstance(servings, str):
            m = re.search(r"(\d+)", servings)
            servings = int(m.group(1)) if m else 4
        elif not isinstance(servings, int):
            servings = 4

        return {
            **base_recipe,
            "ingredients": ingredients,
            "steps": instructions,
            "tags": tags or base_recipe.get("tags", []),
            "prep_time": prep_time or base_recipe.get("prep_time", 0),
            "cook_time": cook_time or base_recipe.get("cook_time", 0),
            "servings": servings,
            "image_url": image_url or base_recipe.get("image_url", ""),
        }
    except Exception:
        return base_recipe


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
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=DEFAULT_HEADERS) as client:
            search_url = f"https://www.marmiton.org/recettes/recherche.aspx?aqt={quote_plus(query)}"
            resp = await client.get(search_url, follow_redirects=True)
            if resp.status_code != 200:
                logger.warning(f"⚠️ Marmiton search status {resp.status_code}, fallback local")
                return _get_fallback_recipes(query)

            base_results = _extract_itemlist_from_search(resp.text, limit)
            if not base_results:
                logger.warning("⚠️ Aucun résultat Marmiton parsé, fallback local")
                return _get_fallback_recipes(query)

            enriched = []
            for item in base_results:
                enriched.append(await _enrich_recipe_from_detail(client, item))

            normalized = [_normalize_marmiton_recipe(recipe) for recipe in enriched]

            # Ne garder que les recettes ayant des détails exploitables
            detailed = []
            for recipe in normalized:
                has_ingredients = False
                try:
                    ingredients = json.loads(recipe.get("ingredients_json", "[]"))
                    has_ingredients = isinstance(ingredients, list) and len(ingredients) > 0
                except Exception:
                    has_ingredients = False

                instructions = (recipe.get("instructions") or "").strip().lower()
                has_real_instructions = bool(instructions) and "voir le site marmiton" not in instructions

                if has_ingredients or has_real_instructions:
                    detailed.append(recipe)

            # Compléter avec fallback local détaillé si nécessaire
            if len(detailed) < limit:
                local_fallback = _get_fallback_recipes(query)
                seen_titles = {r.get("title", "").strip().lower() for r in detailed}
                for recipe in local_fallback:
                    key = recipe.get("title", "").strip().lower()
                    if key and key not in seen_titles:
                        detailed.append(recipe)
                        seen_titles.add(key)
                    if len(detailed) >= limit:
                        break

            logger.info(f"✅ Marmiton scrape: {len(detailed[:limit])} recettes avec détails")
            return detailed[:limit]

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
        import random

        terms = [
            "pâtes", "salade", "soupe", "riz", "quiche", "curry",
            "omelette", "couscous", "lentilles", "gratin", "tofu",
        ]
        random.shuffle(terms)

        collected: list[dict] = []
        seen = set()
        for term in terms[:4]:
            results = await search_marmiton_recipes(term, limit=max(4, count))
            for recipe in results:
                title = (recipe.get("title") or "").strip().lower()
                if title and title not in seen:
                    seen.add(title)
                    collected.append(recipe)
            if len(collected) >= count:
                break

        if collected:
            random.shuffle(collected)
            return collected[:count]

        recipes = _get_fallback_recipes("")
        random.shuffle(recipes)
        return recipes[:count]
    except Exception as e:
        logger.error(f"❌ Random recipes error: {e}")
        return []


def get_marmiton_categories() -> list[str]:
    """Retourne les catégories disponibles sur Marmiton."""
    return MARMITON_CATEGORIES
