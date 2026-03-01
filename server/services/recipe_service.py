"""
FrigoScan — Service de recettes.
Recherche de recettes en ligne (TheMealDB) et base locale de secours.
Calcul du score de correspondance avec le contenu du frigo.
"""

import httpx
import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("frigoscan.recipes")

MEALDB_SEARCH = "https://www.themealdb.com/api/json/v1/1/search.php"
MEALDB_LOOKUP = "https://www.themealdb.com/api/json/v1/1/lookup.php"
MEALDB_RANDOM = "https://www.themealdb.com/api/json/v1/1/random.php"
MEALDB_FILTER = "https://www.themealdb.com/api/json/v1/1/filter.php"
TIMEOUT = 8.0

LOCAL_RECIPES_PATH = Path(__file__).parent.parent / "data" / "local_recipes.json"


def load_local_recipes() -> list[dict]:
    """Charge les recettes locales de secours."""
    if LOCAL_RECIPES_PATH.exists():
        try:
            with open(LOCAL_RECIPES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


async def search_recipes_online(query: str) -> list[dict]:
    """Recherche de recettes via TheMealDB."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(MEALDB_SEARCH, params={"s": query})
            if resp.status_code != 200:
                return []
            data = resp.json()
            meals = data.get("meals") or []
            return [_normalize_mealdb(m) for m in meals]
    except Exception as e:
        logger.warning(f"Erreur recherche recettes: {e}")
        return []


async def get_random_recipes(count: int = 5) -> list[dict]:
    """Récupère des recettes aléatoires."""
    recipes = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for _ in range(count):
                resp = await client.get(MEALDB_RANDOM)
                if resp.status_code == 200:
                    data = resp.json()
                    meals = data.get("meals") or []
                    for m in meals:
                        recipes.append(_normalize_mealdb(m))
    except Exception as e:
        logger.warning(f"Erreur recettes aléatoires: {e}")
    return recipes


def _normalize_mealdb(meal: dict) -> dict:
    """Normalise une recette TheMealDB."""
    ingredients = []
    for i in range(1, 21):
        ing = (meal.get(f"strIngredient{i}") or "").strip()
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        if ing:
            ingredients.append({"name": ing, "measure": measure})

    tags = []
    if meal.get("strTags"):
        tags = [t.strip() for t in meal["strTags"].split(",")]
    if meal.get("strCategory"):
        tags.append(meal["strCategory"])

    return {
        "title": meal.get("strMeal", ""),
        "ingredients_json": json.dumps(ingredients),
        "instructions": meal.get("strInstructions", ""),
        "prep_time": 30,
        "cook_time": 30,
        "servings": 4,
        "source_url": meal.get("strSource", ""),
        "image_url": meal.get("strMealThumb", ""),
        "tags_json": json.dumps(tags),
        "diet_tags_json": "[]",
    }


def compute_match_score(recipe_ingredients_json: str, fridge_items: list[dict]) -> tuple[float, list[str]]:
    """
    Calcule le score de correspondance entre une recette et le contenu du frigo.
    Retourne (score 0-100, liste des ingrédients manquants).
    """
    try:
        ingredients = json.loads(recipe_ingredients_json)
    except Exception:
        return (0.0, [])

    if not ingredients:
        return (0.0, [])

    fridge_names = set()
    for item in fridge_items:
        name = (item.get("name") or "").lower().strip()
        fridge_names.add(name)
        # Ajout de variantes sans accents simplifié
        for word in name.split():
            fridge_names.add(word)

    matched = 0
    missing = []
    for ing in ingredients:
        ing_name = (ing.get("name") or "").lower().strip()
        found = False
        for fn in fridge_names:
            if fn in ing_name or ing_name in fn:
                found = True
                break
        if found:
            matched += 1
        else:
            # On ignore les ingrédients basiques (eau, sel, poivre, huile)
            basic = ["water", "salt", "pepper", "oil", "eau", "sel", "poivre", "huile"]
            if any(b in ing_name for b in basic):
                matched += 1
            else:
                missing.append(ing.get("name", ing_name))

    total = len(ingredients)
    score = round((matched / total) * 100, 1) if total > 0 else 0
    return (score, missing)


def _expand_custom_exclusions(custom_exclusions: list[str]) -> list[str]:
    """Transforme les catégories d'exclusion en mots-clés concrets."""
    category_keywords = {
        "viande_rouge": ["beef", "boeuf", "bœuf", "lamb", "agneau", "veau", "steak", "gibier"],
        "viande_blanche": ["chicken", "poulet", "dinde", "lapin", "canard"],
        "porc": ["pork", "porc", "lardon", "lardons", "bacon", "jambon", "saucisson", "saucisse",
                 "chorizo", "rosette", "andouille", "andouillette", "boudin", "pancetta", "rillettes"],
        "charcuterie": ["lardon", "lardons", "saucisson", "jambon", "bacon", "chorizo", "rosette",
                        "rillettes", "pâté", "andouille", "andouillette", "boudin", "salami",
                        "pancetta", "prosciutto", "merguez"],
        "poisson": ["fish", "poisson", "saumon", "thon", "cabillaud", "sardine", "truite",
                     "maquereau", "dorade", "bar", "anchois"],
        "fruits_de_mer": ["shrimp", "crab", "lobster", "crevette", "crabe", "homard",
                          "moule", "huître", "coquille", "langoustine", "crustacé"],
        "oeufs": ["egg", "oeuf", "oeufs"],
        "produits_laitiers": ["milk", "cream", "cheese", "butter", "lait", "crème", "fromage",
                              "beurre", "yaourt", "mozzarella", "emmental", "comté", "camembert",
                              "crème fraîche"],
        "gluten": ["wheat", "flour", "bread", "pasta", "blé", "farine", "pain", "pâte"],
        "alcool": ["wine", "vin", "beer", "bière", "alcool", "alcohol", "rhum", "vodka", "whisky"],
        "sucre": ["sugar", "sucre", "sirop", "caramel", "chocolat"],
        "friture": ["frit", "frites", "friture", "beignet", "panure"],
    }

    expanded = set()
    for excl in custom_exclusions:
        key = excl.lower().replace(" ", "_")
        if key in category_keywords:
            expanded.update(category_keywords[key])
        else:
            # Mot-clé libre
            expanded.add(key)
    return list(expanded)


def filter_by_diet(recipes: list[dict], diets: list[str], allergens: list[str], custom_exclusions: list[str] = None) -> list[dict]:
    """
    Filtre les recettes selon les régimes et allergènes.
    Retourne les recettes compatibles.
    custom_exclusions : liste de mots-clés supplémentaires pour le régime personnalisé.
    """
    if not diets and not allergens:
        return recipes

    allergen_keywords = {
        "gluten": ["wheat", "flour", "bread", "pasta", "blé", "farine", "pain", "pâte"],
        "lactose": ["milk", "cream", "cheese", "butter", "lait", "crème", "fromage", "beurre"],
        "arachides": ["peanut", "arachide", "cacahuète"],
        "fruits_a_coque": ["almond", "walnut", "hazelnut", "amande", "noix", "noisette"],
        "oeufs": ["egg", "oeuf"],
        "poisson": ["fish", "poisson"],
        "crustaces": ["shrimp", "crab", "lobster", "crevette", "crabe", "homard"],
        "soja": ["soy", "soja", "tofu"],
        "celeri": ["celery", "céleri"],
        "moutarde": ["mustard", "moutarde"],
        "sesame": ["sesame", "sésame"],
        "sulfites": ["wine", "vin", "sulfite"],
        "lupin": ["lupin"],
        "mollusques": ["mussel", "oyster", "moule", "huître", "mollusque"],
    }

    diet_exclude = {
        "végétarien": [
            "chicken", "beef", "pork", "lamb", "poulet", "boeuf", "bœuf", "porc",
            "agneau", "viande", "meat", "fish", "poisson", "lardon", "lardons",
            "saucisse", "saucisson", "jambon", "bacon", "canard", "dinde", "veau",
            "lapin", "steak", "merguez", "chorizo", "rosette", "rillettes",
            "pâté", "gibier", "andouille", "andouillette", "boudin",
            "pancetta", "prosciutto", "salami",
        ],
        "végan": [
            "chicken", "beef", "pork", "lamb", "poulet", "boeuf", "bœuf", "porc",
            "agneau", "viande", "meat", "fish", "poisson", "lardon", "lardons",
            "saucisse", "saucisson", "jambon", "bacon", "canard", "dinde", "veau",
            "lapin", "steak", "merguez", "chorizo", "rosette", "rillettes",
            "pâté", "gibier", "andouille", "andouillette", "boudin",
            "pancetta", "prosciutto", "salami",
            "milk", "cream", "cheese", "butter", "egg", "honey",
            "lait", "crème", "fromage", "beurre", "oeuf", "oeufs", "miel",
            "yaourt", "yogurt", "mozzarella", "emmental", "comté", "camembert",
            "crème fraîche",
        ],
        "pesco_végétarien": [
            "chicken", "beef", "pork", "lamb", "poulet", "boeuf", "bœuf", "porc",
            "agneau", "viande", "meat", "lardon", "lardons",
            "saucisse", "saucisson", "jambon", "bacon", "canard", "dinde", "veau",
            "lapin", "steak", "merguez", "chorizo", "rosette", "rillettes",
            "pâté", "gibier", "andouille", "andouillette", "boudin",
            "pancetta", "prosciutto", "salami",
        ],
        "flexitarien": [
            "beef", "boeuf", "bœuf", "lamb", "agneau", "veau",
            "steak", "gibier",
        ],
        "sans_gluten": allergen_keywords.get("gluten", []),
        "sans_lactose": allergen_keywords.get("lactose", []),
        "halal": [
            "pork", "porc", "lard", "lardon", "lardons", "bacon", "ham", "jambon",
            "saucisson", "rosette", "rillettes", "chorizo", "andouille", "andouillette",
            "boudin", "pancetta", "prosciutto", "salami",
            "wine", "vin", "alcool", "alcohol", "beer", "bière",
        ],
        "casher": ["pork", "porc", "shellfish", "crustacé", "lardon", "lardons"],
    }

    filtered = []
    for recipe in recipes:
        ingredients_str = recipe.get("ingredients_json", "").lower()
        title_str = recipe.get("title", "").lower()
        search_str = ingredients_str + " " + title_str
        is_ok = True

        # Vérifier régimes
        for diet in diets:
            diet_key = diet.lower().replace(" ", "_")

            # Régime personnalisé : utiliser les exclusions custom
            if diet_key == "régime_personnalisé" and custom_exclusions:
                expanded = _expand_custom_exclusions(custom_exclusions)
                for word in expanded:
                    if word.lower() in search_str:
                        is_ok = False
                        break
            else:
                excluded = diet_exclude.get(diet_key, [])
                for word in excluded:
                    if word in search_str:
                        is_ok = False
                        break
            if not is_ok:
                break

        # Vérifier allergènes
        if is_ok:
            for allergen in allergens:
                allergen_key = allergen.lower().replace(" ", "_")
                keywords = allergen_keywords.get(allergen_key, [allergen.lower()])
                for kw in keywords:
                    if kw in ingredients_str:
                        is_ok = False
                        break
                if not is_ok:
                    break

        if is_ok:
            filtered.append(recipe)

    return filtered


def suggest_alternatives(missing_ingredient: str) -> list[str]:
    """Suggère des alternatives pour un ingrédient manquant."""
    alternatives_map = {
        "butter": ["huile d'olive", "margarine", "huile de coco"],
        "beurre": ["huile d'olive", "margarine", "huile de coco"],
        "cream": ["lait de coco", "crème de soja", "yaourt"],
        "crème": ["lait de coco", "crème de soja", "yaourt"],
        "milk": ["lait d'amande", "lait de soja", "lait d'avoine"],
        "lait": ["lait d'amande", "lait de soja", "lait d'avoine"],
        "egg": ["compote de pommes", "graines de chia", "banane"],
        "oeuf": ["compote de pommes", "graines de chia", "banane"],
        "flour": ["farine de riz", "fécule de maïs", "farine de sarrasin"],
        "farine": ["farine de riz", "fécule de maïs", "farine de sarrasin"],
        "chicken": ["tofu", "tempeh", "seitan"],
        "poulet": ["tofu", "tempeh", "seitan"],
        "beef": ["lentilles", "champignons", "protéines de soja"],
        "boeuf": ["lentilles", "champignons", "protéines de soja"],
        "rice": ["quinoa", "boulgour", "couscous"],
        "riz": ["quinoa", "boulgour", "couscous"],
        "pasta": ["nouilles de riz", "spirales de courgette", "gnocchi"],
        "pâtes": ["nouilles de riz", "spirales de courgette", "gnocchi"],
    }
    key = missing_ingredient.lower().strip()
    for k, v in alternatives_map.items():
        if k in key or key in k:
            return v
    return []
