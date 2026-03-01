"""
FrigoScan — Service de recettes.
Recherche de recettes en ligne (TheMealDB + fallback Marmiton).
Calcul du score de correspondance avec le contenu du frigo.
"""

import httpx
import json
import logging
import re
from pathlib import Path
from typing import Optional

from .marmiton_service import (
    search_marmiton_recipes,
    get_random_marmiton_recipes,
    get_marmiton_categories,
)

logger = logging.getLogger("frigoscan.recipes")

MEALDB_SEARCH = "https://www.themealdb.com/api/json/v1/1/search.php"
MEALDB_LOOKUP = "https://www.themealdb.com/api/json/v1/1/lookup.php"
MEALDB_RANDOM = "https://www.themealdb.com/api/json/v1/1/random.php"
MEALDB_FILTER = "https://www.themealdb.com/api/json/v1/1/filter.php"
MEALDB_CATEGORIES = "https://www.themealdb.com/api/json/v1/1/list.php?c=list"
TIMEOUT = 15.0

# API de traduction gratuite MyMemory
TRANSLATION_API = "https://api.mymemory.translated.net/get"
TRANSLATION_TIMEOUT = 3.0

# Dictionnaire de traductions de titres courants EN -> FR
RECIPE_TITLES_FR = {
    "chicken curry": "curry de poulet",
    "chicken fried rice": "riz frit au poulet",
    "beef bourguignon": "boeuf bourguignon",
    "beef stew": "ragoût de boeuf",
    "fish and chips": "poisson frit et frites",
    "fish tacos": "tacos au poisson",
    "pork chops": "côtelettes de porc",
    "lamb roast": "rôti d'agneau",
    "spaghetti carbonara": "spaghetti carbonara",
    "lasagne": "lasagne",
    "pizza margherita": "pizza margherita",
    "grilled vegetables": "legumes grilles",
    "vegetable stir fry": "saute de legumes",
    "caesar salad": "salade cesar",
    "greek salad": "salade grecque",
    "french onion soup": "soupe à l'oignon",
    "mushroom soup": "soupe aux champignons",
    "tomato soup": "soupe à la tomate",
    "chocolate cake": "gateau au chocolat",
    "carrot cake": "gateau aux carottes",
    "apple pie": "tarte aux pommes",
    "cheesecake": "gateau fromage",
    "tiramisu": "tiramisu",
    "brownies": "brownies",
    "ice cream": "glace",
    "pancakes": "crepes",
    "waffles": "gaufres",
    "omelette": "omelette",
    "scrambled eggs": "oeufs brouilles",
    "french toast": "pain perdu",
    "breakfast": "petit-dejeuner",
    "salmon": "saumon",
    "tuna": "thon",
    "shrimp": "crevettes",
    "mussels": "moules",
    "paella": "paella",
    "risotto": "risotto",
    "couscous": "couscous",
    "tajine": "tajine",
    "ramen": "ramen",
    "pad thai": "pad thai",
    "thai green curry": "curry vert thai",
    "tom yum": "tom yum",
    "butter chicken": "poulet au beurre",
    "tandoori chicken": "poulet tandoori",
    "samosa": "samoussa",
    "naan": "naan",
    "biryani": "biryani",
    "falafel": "falafel",
    "hummus": "houmous",
    "shawarma": "shawarma",
    "tempura": "tempura",
    "sushi": "sushi",
    "dim sum": "dim sum",
    "peking duck": "canard de pekin",
    "dumplings": "raviolis",
    "goulash": "goulasch",
    "pierogi": "pierogis",
    "borscht": "bortsch",
    "croissant": "croissant",
    "baguette": "baguette",
    "macaron": "macaron",
    "eclair": "eclair",
    "mille-feuille": "mille-feuille",
}

LOCAL_RECIPES_PATH = Path(__file__).parent.parent / "data" / "local_recipes.json"

# ---- Traduction anglais → français ------------------------------------------------

async def _translate_text_api(text: str, source_lang: str = "en", target_lang: str = "fr") -> str:
    """
    Traduit un texte via l'API MyMemory (gratuite, sans clé).
    Retourne le texte original en cas d'erreur.
    """
    if not text or not text.strip():
        return text
    
    text_lower = text.lower().strip()
    
    # Vérifier le dictionnaire de fallback d'abord
    if text_lower in RECIPE_TITLES_FR:
        return RECIPE_TITLES_FR[text_lower]
    
    # Cherche un mot-clé dans le titre
    for en_key, fr_value in RECIPE_TITLES_FR.items():
        if en_key in text_lower:
            # Remplacer le mot-clé par sa traduction
            translated = text
            for word_en in en_key.split():
                for key, val in RECIPE_TITLES_FR.items():
                    if word_en in key:
                        # Trouver les mots en français correspondants
                        translated = translated.replace(word_en, val.split()[0] if val.split() else val)
                        break
            if translated != text:
                return translated
    
    try:
        async with httpx.AsyncClient(timeout=TRANSLATION_TIMEOUT) as client:
            params = {
                "q": text,
                "langpair": f"{source_lang}|{target_lang}"
            }
            resp = await client.get(TRANSLATION_API, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("responseStatus") == 200:
                    translated = data.get("responseData", {}).get("translatedText", "")
                    if translated and translated.strip() and translated != text:
                        return translated
    except Exception as e:
        logger.warning(f"Erreur traduction API '{text}': {e}")
    
    # En cas d'erreur, retourner l'original
    return text


# Mapping des catégories TheMealDB → français
CATEGORY_FR = {
    "Beef": "Bœuf", "Breakfast": "Petit-déjeuner", "Chicken": "Poulet",
    "Dessert": "Dessert", "Goat": "Chèvre", "Lamb": "Agneau",
    "Miscellaneous": "Divers", "Pasta": "Pâtes", "Pork": "Porc",
    "Seafood": "Fruits de mer", "Side": "Accompagnement", "Starter": "Entrée",
    "Vegan": "Végan", "Vegetarian": "Végétarien",
}
CATEGORY_EN = {v: k for k, v in CATEGORY_FR.items()}  # reverse

# Dictionnaire d'ingrédients EN→FR fréquents
INGREDIENT_FR = {
    "chicken": "poulet", "chicken breast": "blanc de poulet", "chicken thighs": "cuisses de poulet",
    "beef": "bœuf", "pork": "porc", "lamb": "agneau", "salmon": "saumon",
    "tuna": "thon", "shrimp": "crevettes", "prawns": "crevettes",
    "egg": "œuf", "eggs": "œufs", "butter": "beurre", "oil": "huile",
    "olive oil": "huile d'olive", "vegetable oil": "huile végétale",
    "salt": "sel", "pepper": "poivre", "sugar": "sucre", "flour": "farine",
    "milk": "lait", "cream": "crème", "heavy cream": "crème épaisse",
    "sour cream": "crème aigre", "cheese": "fromage", "parmesan cheese": "parmesan",
    "cheddar cheese": "cheddar", "mozzarella": "mozzarella",
    "onion": "oignon", "onions": "oignons", "garlic": "ail", "garlic clove": "gousse d'ail",
    "garlic cloves": "gousses d'ail", "tomato": "tomate", "tomatoes": "tomates",
    "potato": "pomme de terre", "potatoes": "pommes de terre",
    "carrot": "carotte", "carrots": "carottes",
    "celery": "céleri", "mushrooms": "champignons", "mushroom": "champignon",
    "spinach": "épinards", "broccoli": "brocoli", "zucchini": "courgette",
    "bell pepper": "poivron", "red pepper": "poivron rouge", "green pepper": "poivron vert",
    "lettuce": "laitue", "cucumber": "concombre", "avocado": "avocat",
    "lemon": "citron", "lemon juice": "jus de citron", "lime": "citron vert",
    "orange": "orange", "apple": "pomme", "banana": "banane",
    "rice": "riz", "pasta": "pâtes", "noodles": "nouilles", "bread": "pain",
    "spaghetti": "spaghetti", "penne": "penne", "macaroni": "macaroni",
    "water": "eau", "stock": "bouillon", "chicken stock": "bouillon de poulet",
    "beef stock": "bouillon de bœuf", "vegetable stock": "bouillon de légumes",
    "wine": "vin", "red wine": "vin rouge", "white wine": "vin blanc",
    "soy sauce": "sauce soja", "tomato sauce": "sauce tomate",
    "tomato paste": "concentré de tomate", "tomato puree": "purée de tomate",
    "worcestershire sauce": "sauce Worcestershire", "hot sauce": "sauce piquante",
    "mustard": "moutarde", "ketchup": "ketchup", "mayonnaise": "mayonnaise",
    "vinegar": "vinaigre", "balsamic vinegar": "vinaigre balsamique",
    "honey": "miel", "maple syrup": "sirop d'érable",
    "cinnamon": "cannelle", "cumin": "cumin", "paprika": "paprika",
    "oregano": "origan", "basil": "basilic", "thyme": "thym",
    "rosemary": "romarin", "parsley": "persil", "bay leaf": "feuille de laurier",
    "bay leaves": "feuilles de laurier", "chili": "piment", "ginger": "gingembre",
    "nutmeg": "noix de muscade", "turmeric": "curcuma", "coriander": "coriandre",
    "vanilla": "vanille", "vanilla extract": "extrait de vanille",
    "chocolate": "chocolat", "cocoa": "cacao",
    "baking powder": "levure chimique", "baking soda": "bicarbonate de soude",
    "yeast": "levure", "cornstarch": "fécule de maïs",
    "bacon": "bacon", "ham": "jambon", "sausage": "saucisse",
    "coconut milk": "lait de coco", "coconut": "noix de coco",
    "peanut butter": "beurre de cacahuète", "almonds": "amandes",
    "walnuts": "noix", "cashews": "noix de cajou", "pine nuts": "pignons de pin",
    "sesame oil": "huile de sésame", "sesame seeds": "graines de sésame",
    "breadcrumbs": "chapelure", "plain flour": "farine", "self-raising flour": "farine avec levure",
    "double cream": "crème épaisse", "single cream": "crème liquide",
    "spring onions": "oignons verts", "red onion": "oignon rouge", "red onions": "oignons rouges",
    "cherry tomatoes": "tomates cerise", "chopped tomatoes": "tomates concassées",
    "canned tomatoes": "tomates en conserve", "sun-dried tomatoes": "tomates séchées",
    "green beans": "haricots verts", "kidney beans": "haricots rouges",
    "chickpeas": "pois chiches", "lentils": "lentilles",
    "frozen peas": "petits pois surgelés", "peas": "petits pois",
    "sweetcorn": "maïs doux", "corn": "maïs",
    "chili powder": "poudre de piment", "cayenne pepper": "poivre de Cayenne",
    "black pepper": "poivre noir", "white pepper": "poivre blanc",
    "fish sauce": "sauce poisson (nuoc-mâm)", "oyster sauce": "sauce huître",
    "rice vinegar": "vinaigre de riz", "mirin": "mirin",
    "dried oregano": "origan séché", "dried basil": "basilic séché",
    "dried thyme": "thym séché", "mixed herbs": "herbes mélangées",
    "salsa": "salsa", "pesto": "pesto",
    "cream cheese": "fromage frais", "ricotta": "ricotta",
    "feta": "feta", "gouda": "gouda", "gruyere": "gruyère",
    "whipping cream": "crème fouettée", "ice cream": "glace",
    "brown sugar": "sucre roux", "icing sugar": "sucre glace",
    "caster sugar": "sucre en poudre", "demerara sugar": "cassonade",
    "dark chocolate": "chocolat noir", "white chocolate": "chocolat blanc",
    "milk chocolate": "chocolat au lait",
    "strawberries": "fraises", "blueberries": "myrtilles", "raspberries": "framboises",
    "mango": "mangue", "pineapple": "ananas", "peach": "pêche",
    "apricot": "abricot", "plum": "prune", "pear": "poire", "grapes": "raisin",
    "leek": "poireau", "turnip": "navet", "cabbage": "chou",
    "cauliflower": "chou-fleur", "kale": "chou frisé", "aubergine": "aubergine",
    "eggplant": "aubergine", "courgette": "courgette", "asparagus": "asperges",
    "artichoke": "artichaut", "beetroot": "betterave", "radish": "radis",
    "fennel": "fenouil", "endive": "endive",
    "tofu": "tofu", "tempeh": "tempeh",
    "lemongrass": "citronnelle", "lemongrass stalk": "tige de citronnelle", "lemongrass stalks": "tiges de citronnelle",
    "lime juice": "jus de citron vert", "lime zest": "zeste de citron vert",
    "coriander leaves": "feuilles de coriandre", "coriander seeds": "graines de coriandre",
    "five spice powder": "cinq épices", "five-spice": "cinq épices", "chinese five spice powder": "cinq épices",
    "white bread": "pain blanc", "wheat bread": "pain complet",
    "rice noodles": "nouilles de riz", "egg noodles": "nouilles aux œufs",
    "red wine vinegar": "vinaigre de vin rouge", "white vinegar": "vinaigre blanc",
    "lime leaves": "feuilles de citron vert", "thai basil": "basilic thaï",
    "thai red curry paste": "pâte de curry rouge thaï", "thai green curry paste": "pâte de curry vert thaï",
    "allspice": "piment de la Jamaïque", "allspices": "piment de la Jamaïque",
    "basil leaves": "feuilles de basilic", "cilantro leaves": "feuilles de coriandre", "mint leaves": "feuilles de menthe",
    "zest of": "zeste de", "juice of": "jus de", "for brushing": "pour badigeonner",
    "egg plants": "aubergines", "ground meat": "viande moulue", "unwaxed lemon": "citron non ciré",
    "unwaxed lime": "citron vert non ciré", "handful": "poignée",
}

def _translate_ingredient_name(name_en: str) -> str:
    """Traduit un nom d'ingrédient anglais en français."""
    import re

    key = (name_en or "").lower().strip()
    if not key:
        return ""

    prep_map = {
        "finely chopped": "finement haché",
        "roughly chopped": "grossièrement haché",
        "finely sliced": "finement tranché",
        "chopped": "haché",
        "minced": "émincé",
        "diced": "en dés",
        "sliced": "tranché",
        "crushed": "écrasé",
        "grated": "râpé",
        "ground": "moulu",
    }

    # Traduction directe prioritaire
    phrase_overrides = {
        "egg white": "blanc d'œuf",
        "egg whites": "blancs d'œufs",
        "red wine vinegar": "vinaigre de vin rouge",
        "black beans": "haricots noirs",
        "white beans": "haricots blancs",
        "black olives": "olives noires",
        "green chilli": "piment vert",
        "green chilies": "piments verts",
        "red chilli": "piment rouge",
        "red chilli powder": "poudre de piment rouge",
        "white bread": "pain blanc",
        "desiccated coconut": "noix de coco râpée",
        "romano pepper": "poivron romano",
        "king prawns": "crevettes royales",
        "raw king prawns": "crevettes royales crues",
        "squid": "calamar",
    }

    if key in phrase_overrides:
        return phrase_overrides[key]

    if key in INGREDIENT_FR:
        return INGREDIENT_FR[key]
    if key.endswith('s') and key[:-1] in INGREDIENT_FR:
        return INGREDIENT_FR[key[:-1]]

    # Extraire un qualificatif culinaire éventuel
    prep_found = ""
    base = key
    for prep_en in sorted(prep_map.keys(), key=len, reverse=True):
        if prep_en in base:
            prep_found = prep_en
            base = re.sub(rf"\b{re.escape(prep_en)}\b", "", base).strip()
            break

    base = re.sub(r"\s+", " ", base).strip(" ,.-")
    if not base:
        base = key

    # Re-traduction exacte sur base nettoyée
    if base in INGREDIENT_FR:
        base_fr = INGREDIENT_FR[base]
    elif base.endswith('s') and base[:-1] in INGREDIENT_FR:
        base_fr = INGREDIENT_FR[base[:-1]]
    else:
        # Fallback mot à mot (utile pour "red onion", "onions", etc.)
        token_overrides = {
            "large": "grand",
            "medium": "moyen",
            "small": "petit",
            "red": "rouge",
            "green": "vert",
            "white": "blanc",
            "black": "noir",
            "raw": "cru",
            "dried": "séché",
            "desiccated": "râpé",
            "king": "royal",
        }

        translated_words = []
        for w in base.split():
            w_clean = w.strip(" ,.-")
            if not w_clean:
                continue
            if w_clean in token_overrides:
                translated_words.append(token_overrides[w_clean])
            elif w_clean in INGREDIENT_FR:
                translated_words.append(INGREDIENT_FR[w_clean])
            elif w_clean.endswith('s') and w_clean[:-1] in INGREDIENT_FR:
                translated_words.append(INGREDIENT_FR[w_clean[:-1]])
            else:
                translated_words.append(w_clean)

        # Réordonner légèrement pour un français plus naturel
        size_tokens = {"petit", "petite", "petits", "petites", "grand", "grande", "grands", "grandes", "moyen", "moyenne", "moyens", "moyennes"}
        color_state_tokens = {"rouge", "rouges", "vert", "verte", "verts", "vertes", "blanc", "blanche", "blancs", "blanches", "noir", "noire", "noirs", "noires", "cru", "crue", "crus", "crues", "séché", "séchée", "séchés", "séchées", "râpé", "râpée", "râpés", "râpées"}
        if len(translated_words) >= 2:
            core = [w for w in translated_words if w not in size_tokens and w not in color_state_tokens]
            sizes = [w for w in translated_words if w in size_tokens]
            states = [w for w in translated_words if w in color_state_tokens]
            if core:
                translated_words = sizes + core + states

        base_fr = " ".join(translated_words).strip() or name_en

    if not prep_found:
        return base_fr

    prep_fr = prep_map[prep_found]

    def _agree_prep(prep_text: str, noun_fr: str) -> str:
        import re
        p = prep_text
        n = (noun_fr or "").strip().lower()

        is_plural = n.endswith("s")
        is_feminine = n.endswith("e") or n.endswith("es")

        endings = {
            "é": ("é", "ée", "és", "ées"),
            "u": ("u", "ue", "us", "ues"),
        }

        for stem_end, forms in endings.items():
            masc_s, fem_s, masc_p, fem_p = forms
            if re.search(rf"{stem_end}$", p):
                if is_feminine and is_plural:
                    return re.sub(rf"{stem_end}$", fem_p, p)
                if is_feminine:
                    return re.sub(rf"{stem_end}$", fem_s, p)
                if is_plural:
                    return re.sub(rf"{stem_end}$", masc_p, p)
                return p
        return p

    prep_fr = _agree_prep(prep_fr, base_fr)
    out = f"{base_fr} {prep_fr}".strip()
    out = re.sub(r"\s+", " ", out)
    out = re.sub(r"\bd\'\s+", "d'", out)
    return out


def _translate_measure(measure_en: str) -> str:
    """Traduit les unités de mesure anglaises en français."""
    if not measure_en:
        return measure_en
    m = measure_en.strip().lower()
    # Mapping des unités
    units_map = {
        'teaspoon': 'c. à café', 'teaspoons': 'c. à café', 'tsp': 'c. à café', 'tsp.': 'c. à café',
        'tablespoon': 'c. à soupe', 'tablespoons': 'c. à soupe', 'tbsp': 'c. à soupe',
        'tbs': 'c. à soupe', 'tbsp.': 'c. à soupe', 'tbs.': 'c. à soupe',
        'tblsp': 'c. à soupe', 'tblsp.': 'c. à soupe',
        'tbls': 'c. à soupe', 'tbls.': 'c. à soupe',
        'cup': 'tasse', 'cups': 'tasse', 'cup.': 'tasse', 'c': 'tasse',
        'quart': 'quart', 'quarts': 'quarts', 'qt': 'quart', 'qt.': 'quart',
        'ounce': 'once', 'ounces': 'once', 'oz': 'once', 'oz.': 'once',
        'pound': 'livre', 'pounds': 'livre', 'lb': 'livre', 'lbs': 'livre', 'lbs.': 'livre',
        'gram': 'g', 'grams': 'g', 'g': 'g', 'gr': 'g', 'gr.': 'g',
        'kilogram': 'kg', 'kg': 'kg',
        'milliliter': 'mL', 'milliliters': 'mL', 'ml': 'mL', 'ml.': 'mL',
        'centiliter': 'cL', 'centiliters': 'cL', 'cl': 'cL', 'cl.': 'cL',
        'liter': 'L', 'liters': 'L', 'l': 'L', 'l.': 'L',
        'pinch': 'pincée', 'pinches': 'pincée', 'pinch.': 'pincée',
        'dash': 'trait', 'dashes': 'trait',
        'splash': 'trait', 'splashes': 'trait',
        'clove': 'gousse', 'cloves': 'gousses', 'clove.': 'gousse', 'cloves.': 'gousses',
        'leaf': 'feuille', 'leaves': 'feuilles', 'leaf.': 'feuille', 'leaves.': 'feuilles',
        'sprinkling': 'pincée', 'sprinkle': 'pincée', 'sprinkles': 'pincée',
        'topping': 'garniture', 'toppings': 'garniture',
    }
    pluralizable_units = {'tasse', 'once', 'livre', 'pincée', 'trait', 'gousse', 'quart'}
    phrase_map = {
        'finely chopped': 'finement haché',
        'roughly chopped': 'grossièrement haché',
        'finely sliced': 'finement tranché',
        'chopped': 'haché',
        'minced': 'émincé',
        'diced': 'en dés',
        'sliced': 'tranché',
        'crushed': 'écrasé',
        'grated': 'râpé',
        'ground': 'moulu',
        'cloves minced': 'gousses émincées',
        'clove minced': 'gousse émincée',
        'cloves chopped': 'gousses hachées',
        'clove chopped': 'gousse hachée',
        'to serve': 'à servir',
        'to taste': 'selon le goût',
        'for brushing': 'pour badigeonner',
        'juice of': 'jus de',
        'zest of': 'zeste de',
    }

    def _parse_qty(text: str) -> float | None:
        from fractions import Fraction
        try:
            q = (text or "").strip()
            if not q:
                return None
            if ' ' in q and '/' in q:
                main, frac = q.split(' ', 1)
                return float(main) + float(Fraction(frac))
            if '/' in q:
                return float(Fraction(q))
            return float(q.replace(',', '.'))
        except Exception:
            return None

    def _translate_unit_phrase(text: str) -> str:
        import re
        out = (text or "").strip().lower()
        if not out:
            return out

        # D'abord les expressions multi-mots
        for src in sorted(phrase_map.keys(), key=len, reverse=True):
            out = re.sub(rf"\b{re.escape(src)}\b", phrase_map[src], out)

        # Puis mot à mot pour les unités
        words = []
        for w in out.split():
            words.append(units_map.get(w, w))
        translated = " ".join(words).strip()
        translated = re.sub(r"\s+", " ", translated)
        translated = re.sub(r"\bd\'\s+", "d'", translated)
        return translated

    # Chercher l'unité (la partie sans les chiffres)
    import re
    match = re.match(r'^([\d.,/\s]*)(.*)$', measure_en.strip())
    if match:
        qty_part = match.group(1).strip()  # e.g. "1/2", "250"
        unit_part = match.group(2).strip().lower()  # e.g. "cup", "ml"
        
        # Traduire l'unité
        translated_unit = _translate_unit_phrase(unit_part)

        # Pluralisation simple des unités françaises
        qty_value = _parse_qty(qty_part)
        if qty_value is not None and qty_value > 1 and translated_unit in pluralizable_units and not translated_unit.endswith('s'):
            translated_unit = f"{translated_unit}s"
        
        # Recombiner
        if qty_part:
            return f"{qty_part} {translated_unit}".strip()
        else:
            return translated_unit
    return measure_en


def _adapt_and_translate_measure(measure_en: str, ratio: float) -> str:
    """Adapte les quantités selon le ratio et traduit les unités.
    
    Args:
        measure_en: Mesure originale en anglais (ex: "2 cups", "1/2 tsp")
        ratio: Ratio d'adaptation (ex: 1.5 pour passer de 4 à 6 personnes)
    """
    if not measure_en or not measure_en.strip():
        return ""
    
    import re
    from fractions import Fraction
    
    # Extraire quantité et unité
    match = re.match(r'^([\d.,/\s]+)(.*)$', measure_en.strip())
    if not match:
        # Pas de quantité numérique, juste traduire l'unité/texte
        return _translate_measure(measure_en)
    
    qty_str = match.group(1).strip()
    unit_str = match.group(2).strip()
    
    try:
        # Gérer les fractions (1/2, 1/4, etc.)
        if ' ' in qty_str and '/' in qty_str:
            # Ex: "1 1/2"
            main, frac = qty_str.split(' ', 1)
            qty = float(main) + float(Fraction(frac))
        elif '/' in qty_str:
            qty = float(Fraction(qty_str))
        else:
            qty = float(qty_str.replace(',', '.'))
        
        # Appliquer le ratio
        adapted_qty = qty * ratio
        
        # Formater joliment
        if adapted_qty == int(adapted_qty):
            qty_formatted = str(int(adapted_qty))
        else:
            # Arrondir à 1 décimale si proche
            if abs(adapted_qty - round(adapted_qty, 1)) < 0.01:
                qty_formatted = f"{adapted_qty:.1f}"
            else:
                qty_formatted = f"{adapted_qty:.2f}"
        
        # Traduire l'unité
        measure_adapted = f"{qty_formatted} {unit_str}"
        return _translate_measure(measure_adapted)
        
    except (ValueError, ZeroDivisionError):
        # Si échec du parsing, juste traduire tel quel
        return _translate_measure(measure_en)


def _detect_diet_tags(meal: dict, ingredients_lower: list[str]) -> list[str]:
    """Détecte les régimes alimentaires compatibles avec une recette TheMealDB.
    
    Args:
        meal: Données de la recette
        ingredients_lower: Liste des ingrédients en minuscules
    
    Returns:
        Liste des tags de régime (ex: ["végétarien", "sans_gluten"])
    """
    diet_tags = []
    
    # Vérifier si la recette contient de la viande/poisson
    meat_keywords = [
        "chicken", "beef", "pork", "lamb", "turkey", "duck", "veal",
        "bacon", "ham", "sausage", "meat", "steak", "ground beef",
        "fish", "salmon", "tuna", "cod", "shrimp", "prawn", "crab",
        "lobster", "mussel", "oyster", "seafood", "anchovy"
    ]
    
    has_meat = any(meat in ing for ing in ingredients_lower for meat in meat_keywords)
    
    # Vérifier les produits laitiers
    dairy_keywords = ["milk", "cream", "cheese", "butter", "yogurt", "yoghurt"]
    has_dairy = any(dairy in ing for ing in ingredients_lower for dairy in dairy_keywords)
    
    # Vérifier les œufs
    has_eggs = any("egg" in ing for ing in ingredients_lower)
    
    # Vérifier le miel
    has_honey = any("honey" in ing for ing in ingredients_lower)
    
    # Classification
    if not has_meat:
        diet_tags.append("végétarien")
        
        if not has_dairy and not has_eggs and not has_honey:
            diet_tags.append("végan")
    
    # Vérifier sans gluten (pas de farine, pain, pâtes)
    gluten_keywords = ["flour", "bread", "pasta", "wheat", "noodle", "spaghetti", "couscous"]
    has_gluten = any(gluten in ing for ing in ingredients_lower for gluten in gluten_keywords)
    
    if not has_gluten:
        diet_tags.append("sans_gluten")
    
    # Vérifier sans lactose
    if not has_dairy:
        diet_tags.append("sans_lactose")
    
    return diet_tags


async def _translate_instructions_full(text: str) -> str:
    """
    Traduit les instructions COMPLÈTEMENT de l'anglais vers le français via API.
    Cela évite les mélanges français/anglais.
    """
    if not text or len(text.strip()) < 10:
        return text
    
    # Ne pas traduire si déjà en français (heuristique)
    french_words = ['cuire', 'ajouter', 'mélanger', 'chauffer', 'versez', 'pendant', 
                    'jusqu\'à', 'servir', 'égoutter', 'metter', 'mettre', 'laisser']
    text_lower = text.lower()
    french_count = sum(1 for word in french_words if word in text_lower)
    if french_count > len(french_words) * 0.3:  # Si > 30% de mots français
        return text
    
    try:
        async with httpx.AsyncClient(timeout=TRANSLATION_TIMEOUT) as client:
            params = {
                "q": text,
                "langpair": "en|fr"
            }
            resp = await client.get(TRANSLATION_API, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("responseStatus") == 200:
                    translated = data.get("responseData", {}).get("translatedText", "")
                    if translated and translated.strip() and translated != text:
                        logger.info(f"Instructions traduites avec succès ({len(text)} chars -> {len(translated)} chars)")
                        return translated
    except Exception as e:
        logger.warning(f"Erreur traduction instructions: {e}")
    
    return text


def _translate_recipe(recipe: dict) -> dict:
    """Traduit une recette normalisée (titre, ingrédients et instructions traduits)."""
    # Traduire le titre (garder l'original si échec)
    # Note : la traduction du titre sera faite de manière asynchrone dans get_recipes_by_category
    
    # Traduire les ingrédients
    try:
        ingredients = json.loads(recipe.get("ingredients_json", "[]"))
        for ing in ingredients:
            if ing.get("name"):
                ing["name"] = _translate_ingredient_name(ing["name"])
            if ing.get("measure"):
                ing["measure"] = _translate_measure(ing["measure"])
        recipe["ingredients_json"] = json.dumps(ingredients)
    except Exception:
        pass

    # Traduire les instructions
    if recipe.get("instructions"):
        recipe["instructions"] = _translate_instructions(recipe["instructions"])

    # Traduire les tags
    try:
        tags = json.loads(recipe.get("tags_json", "[]"))
        recipe["tags_json"] = json.dumps([CATEGORY_FR.get(t, t) for t in tags])
    except Exception:
        pass

    return recipe


async def _translate_recipe_async(recipe: dict) -> dict:
    """
    Traduit une recette de manière asynchrone (titre + ingrédients + instructions).
    Utilise l'API MyMemory pour traduire le titre et les instructions.
    """
    # Traduire le titre via API
    if recipe.get("title"):
        original_title = recipe["title"]
        translated_title = await _translate_text_api(original_title, "en", "fr")
        recipe["title"] = translated_title
    
    # Traduire les ingrédients
    try:
        ingredients = json.loads(recipe.get("ingredients_json", "[]"))
        for ing in ingredients:
            if ing.get("name"):
                ing["name"] = _translate_ingredient_name(ing["name"])
            if ing.get("measure"):
                ing["measure"] = _translate_measure(ing["measure"])
        recipe["ingredients_json"] = json.dumps(ingredients)
    except Exception:
        pass

    # Traduire les instructions COMPLÈTEMENT
    if recipe.get("instructions"):
        recipe["instructions"] = await _translate_instructions_full(recipe["instructions"])

    # Traduire les tags
    try:
        tags = json.loads(recipe.get("tags_json", "[]"))
        recipe["tags_json"] = json.dumps([CATEGORY_FR.get(t, t) for t in tags])
    except Exception:
        pass

    return recipe


# Mapping des catégories françaises pour l'UI
RECIPE_CATEGORIES_FR = [
    # Catégories TheMealDB (filtre par catégorie)
    {"id": "Chicken", "label": "Poulet", "type": "filter"},
    {"id": "Beef", "label": "Bœuf", "type": "filter"},
    {"id": "Pork", "label": "Porc", "type": "filter"},
    {"id": "Lamb", "label": "Agneau", "type": "filter"},
    {"id": "Seafood", "label": "Fruits de mer", "type": "filter"},
    {"id": "Pasta", "label": "Pâtes", "type": "filter"},
    {"id": "Vegetarian", "label": "Végétarien", "type": "filter"},
    {"id": "Vegan", "label": "Végan", "type": "filter"},
    {"id": "Dessert", "label": "Dessert", "type": "filter"},
    {"id": "Breakfast", "label": "Petit-déjeuner", "type": "filter"},
    {"id": "Starter", "label": "Entrée", "type": "filter"},
    {"id": "Side", "label": "Accompagnement", "type": "filter"},
    # Par type de repas (multi-recherche pour plus de variété)
    {"id": "lunch", "label": "Déjeuner", "type": "multi", "terms": ["salad", "sandwich", "soup", "wrap", "omelette", "quiche", "lunch"]},
    {"id": "dinner", "label": "Dîner", "type": "multi", "terms": ["stew", "roast", "curry", "casserole", "pie", "gratin", "dinner"]},
    # Par mot-clé (recherche)
    {"id": "soup", "label": "Soupes", "type": "search"},
    {"id": "salad", "label": "Salades", "type": "search"},
    {"id": "rice", "label": "Riz", "type": "search"},
    {"id": "curry", "label": "Curry", "type": "search"},
    {"id": "cake", "label": "Gâteaux", "type": "search"},
    {"id": "Miscellaneous", "label": "Divers", "type": "filter"},
]


async def get_recipes_by_category(category: str, max_results: int = 12, target_servings: int = 4) -> list[dict]:
    """Récupère des recettes par catégorie (filter TheMealDB), recherche ou multi-recherche."""
    import random as rnd

    # Chercher le type de catégorie
    cat_info = next((c for c in RECIPE_CATEGORIES_FR if c["id"] == category), None)
    cat_type = (cat_info or {}).get("type", "filter")

    if cat_type == "search":
        results = await search_recipes_online(category, target_servings=target_servings)
        rnd.shuffle(results)
        return results[:max_results]

    if cat_type == "multi":
        terms = (cat_info or {}).get("terms", [category])
        all_recipes = []
        rnd.shuffle(terms)
        for term in terms[:4]:
            results = await search_recipes_online(term, target_servings=target_servings)
            all_recipes.extend(results)
        rnd.shuffle(all_recipes)
        seen = set()
        unique = []
        for r in all_recipes:
            t = r.get("title", "").lower().strip()
            if t and t not in seen:
                seen.add(t)
                unique.append(r)
        return unique[:max_results]

    # Type "filter" — catégorie TheMealDB
    recipes = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(MEALDB_FILTER, params={"c": category})
            if resp.status_code != 200:
                # Fallback : chercher par mot-clé
                logger.info(f"Catégorie {category} ne retourne rien, fallback recherche")
                return await search_recipes_online(category, target_servings=target_servings)
            data = resp.json()
            meals = data.get("meals") or []
            if not meals:
                # Fallback : chercher par mot-clé
                return await search_recipes_online(category, target_servings=target_servings)
            rnd.shuffle(meals)
            meals = meals[:max_results + 5]  # Charger plus au cas où certains échouent
            for meal in meals:
                meal_id = meal.get("idMeal")
                if not meal_id:
                    continue
                try:
                    detail_resp = await client.get(MEALDB_LOOKUP, params={"i": meal_id})
                    if detail_resp.status_code == 200:
                        detail_data = detail_resp.json()
                        detail_meals = detail_data.get("meals") or []
                        if detail_meals:
                            recipe = _normalize_mealdb(detail_meals[0], target_servings=target_servings)
                            recipe = await _translate_recipe_async(recipe)
                            recipes.append(recipe)
                    if len(recipes) >= max_results:
                        break  # Arrêter une fois qu'on a assez
                except Exception as e:
                    logger.warning(f"Erreur lookup {meal_id}: {e}")
                    continue
    except Exception as e:
        logger.warning(f"Erreur recettes par catégorie {category}: {e}")
        # Dernière tentative : recherche par mot-clé
        try:
            return await search_recipes_online(category, target_servings=target_servings)
        except Exception:
            pass
    return recipes[:max_results]


def _normalize_marmiton_to_recipe_format(recipe: dict) -> dict:
    """Convertit une recette Marmiton au format interne."""
    # Convertir liste d'ingrédients simples en format ingredients_json
    ingredients = []
    for ing in recipe.get("ingredients", []):
        if isinstance(ing, str):
            ingredients.append({"name": ing, "measure": ""})
        else:
            ingredients.append(ing)
    
    # Convertir steps en instructions
    steps = recipe.get("steps", [])
    instructions = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)]) if steps else ""
    
    tags = recipe.get("tags", [])
    raw_image_url = (recipe.get("image_url") or "").strip()
    image_url = raw_image_url if raw_image_url.startswith("http") else ""

    return {
        "title": recipe.get("title", ""),
        "ingredients_json": json.dumps(ingredients),
        "instructions": instructions,
        "prep_time": recipe.get("prep_time", 30),
        "cook_time": recipe.get("cook_time", 30),
        "servings": recipe.get("servings", 4),
        "source_url": "",
        "image_url": image_url,
        "tags_json": json.dumps(tags),
        "diet_tags_json": json.dumps(["végétarien"]),  # Les recettes Marmiton sont toutes végétariennes
    }


def load_local_recipes() -> list[dict]:
    """Charge les recettes locales de secours (local_recipes.json + marmiton_fallback.json)."""
    recipes = []
    
    # Charger local_recipes.json
    if LOCAL_RECIPES_PATH.exists():
        try:
            with open(LOCAL_RECIPES_PATH, "r", encoding="utf-8") as f:
                recipes.extend(json.load(f))
        except Exception as e:
            logger.warning(f"Erreur chargement local_recipes.json: {e}")
    
    # Charger marmiton_fallback.json
    fallback_path = Path(__file__).parent.parent / "data" / "marmiton_fallback.json"
    if fallback_path.exists():
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                marmiton_recipes = json.load(f)
                # Convertir au format interne
                for recipe in marmiton_recipes:
                    recipes.append(_normalize_marmiton_to_recipe_format(recipe))
                logger.info(f"Chargé {len(marmiton_recipes)} recettes Marmiton")
        except Exception as e:
            logger.warning(f"Erreur chargement marmiton_fallback.json: {e}")
    
    return recipes


async def search_recipes_online(query: str, target_servings: int = 4) -> list[dict]:
    """Recherche de recettes via TheMealDB (fallback Marmiton)."""
    query = (query or "").strip()
    if not query:
        return []

    def _query_candidates(raw_query: str) -> list[str]:
        candidates: list[str] = []
        seen: set[str] = set()

        def add(value: str):
            value = (value or "").strip()
            if not value:
                return
            key = value.lower()
            if key in seen:
                return
            seen.add(key)
            candidates.append(value)

        add(raw_query)

        q_lower = raw_query.lower().strip()
        add(CATEGORY_EN.get(raw_query, ""))
        add(CATEGORY_EN.get(q_lower.capitalize(), ""))

        # Traduction FR -> EN simple basée sur le dictionnaire d'ingrédients existant.
        fr_to_en = {fr.lower(): en for en, fr in INGREDIENT_FR.items()}
        add(fr_to_en.get(q_lower, ""))

        # Heuristique: supprimer pluriel simple.
        if q_lower.endswith("s"):
            singular = q_lower[:-1]
            add(fr_to_en.get(singular, ""))

        return candidates

    try:
        recipes: list[dict] = []
        seen_titles: set[str] = set()
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for candidate in _query_candidates(query):
                resp = await client.get(MEALDB_SEARCH, params={"s": candidate})
                if resp.status_code != 200:
                    continue

                data = resp.json()
                meals = data.get("meals") or []
                for meal in meals:
                    normalized = _normalize_mealdb(meal, target_servings=target_servings)
                    title_key = (normalized.get("title") or "").strip().lower()
                    if not title_key or title_key in seen_titles:
                        continue
                    seen_titles.add(title_key)
                    recipes.append(normalized)

                if len(recipes) >= 24:
                    break

        if recipes:
            logger.info(f"TheMealDB: {len(recipes)} recettes trouvées pour '{query}'")
            return recipes
    except Exception as e:
        logger.warning(f"Erreur recherche recettes TheMealDB: {e}")

    try:
        fallback = await search_marmiton_recipes(query)
        logger.info(f"Fallback Marmiton: {len(fallback)} recettes trouvées pour '{query}'")
        return fallback
    except Exception as e:
        logger.warning(f"Erreur fallback Marmiton: {e}")
        return []


async def get_random_recipes(count: int = 5, target_servings: int = 4) -> list[dict]:
    """Récupère des recettes aléatoires via TheMealDB (fallback Marmiton)."""
    safe_count = max(1, min(count, 24))

    try:
        recipes: list[dict] = []
        seen_titles: set[str] = set()
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            max_attempts = safe_count * 3
            for _ in range(max_attempts):
                if len(recipes) >= safe_count:
                    break

                resp = await client.get(MEALDB_RANDOM)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                meals = data.get("meals") or []
                if not meals:
                    continue

                normalized = _normalize_mealdb(meals[0], target_servings=target_servings)
                title_key = (normalized.get("title") or "").strip().lower()
                if not title_key or title_key in seen_titles:
                    continue

                seen_titles.add(title_key)
                recipes.append(normalized)

        if recipes:
            logger.info(f"TheMealDB: {len(recipes)} recettes aléatoires récupérées")
            return recipes
    except Exception as e:
        logger.warning(f"Erreur recettes aléatoires TheMealDB: {e}")

    try:
        fallback = await get_random_marmiton_recipes(safe_count)
        logger.info(f"Fallback Marmiton: {len(fallback)} recettes aléatoires récupérées")
        return fallback
    except Exception as e:
        logger.warning(f"Erreur fallback aléatoire Marmiton: {e}")
        return []


async def enrich_recipe_images_with_marmiton(recipes: list[dict], max_to_enrich: int = 8) -> list[dict]:
    """
    Enrichit les images de recettes via Marmiton quand elles sont absentes ou génériques.
    """
    enriched_count = 0
    for recipe in recipes:
        if enriched_count >= max_to_enrich:
            break

        current_image = recipe.get("image_url", "") or ""
        is_generic = current_image.startswith("data:image/svg+xml") or not current_image
        if not is_generic:
            continue

        title = (recipe.get("title") or "").strip()
        if not title:
            continue

        try:
            candidates = await search_marmiton_recipes(title, limit=1)
            if not candidates:
                continue

            candidate_img = (candidates[0].get("image_url") or "").strip()
            if candidate_img.startswith("http"):
                recipe["image_url"] = candidate_img
                enriched_count += 1
        except Exception:
            continue

    return recipes


def _normalize_mealdb(meal: dict, target_servings: int = 4) -> dict:
    """Normalise une recette TheMealDB avec traduction et adaptation des quantités.
    
    Args:
        meal: Données brutes de la recette TheMealDB
        target_servings: Nombre de personnes cible (défaut 4)
    """
    # Servings originaux de TheMealDB (généralement 4)
    original_servings = 4
    ratio = target_servings / original_servings if original_servings > 0 else 1.0
    
    # Extraire et traduire les ingrédients avec adaptation des quantités
    ingredients = []
    all_ingredients_lower = []
    
    import re

    prep_terms = sorted([
        "finely chopped", "roughly chopped", "finely sliced", "thinly sliced",
        "chopped", "minced", "diced", "sliced", "crushed", "grated", "ground",
        "large", "medium", "small",
        "finely", "roughly", "thinly"
    ], key=len, reverse=True)

    def _needs_de_prefix(measure_fr: str) -> bool:
        import re
        m = (measure_fr or "").lower()
        if not m:
            return False
        # Détecter la présence d'une unité réelle (et éviter les faux positifs comme la lettre "l" dans "finely").
        if re.search(r"c\.\s*à\s*(café|soupe)", m):
            return True
        unit_tokens = {
            "tasse", "tasses", "quart", "quarts", "once", "onces", "livre", "livres",
            "pincée", "pincées", "trait", "traits", "gousse", "gousses",
            "g", "kg", "ml", "cl", "l", "mL", "cL", "L"
        }
        words = re.findall(r"[a-zA-ZÀ-ÿ\.]+", m)
        return any(w in unit_tokens for w in words)

    def _add_de_prefix(name_fr: str) -> str:
        n = (name_fr or "").strip()
        if not n:
            return n
        nl = n.lower()
        if nl.startswith("de ") or nl.startswith("d'"):
            return n
        vowels = ("a", "e", "i", "o", "u", "y", "h", "à", "â", "é", "è", "ê", "ë", "î", "ï", "ô", "ù", "û", "ü")
        return f"d'{n}" if nl.startswith(vowels) else f"de {n}"

    def _agree_prep_with_measure(name_fr: str, measure_fr: str) -> str:
        n = (name_fr or "").strip()
        m = (measure_fr or "").lower()
        if not n:
            return n

        words = n.split()
        if not words:
            return n

        idx = 0
        if words[0].lower() in {"de", "d'"} and len(words) > 1:
            idx = 1

        noun = words[idx].lower()
        is_plural = noun.endswith("s")
        is_feminine = noun.endswith("e") or noun.endswith("es")

        # Fallback par la mesure (utile quand le nom commence par d'...)
        if any(token in m for token in ["gousses", "tasses", "onces", "livres", "pincées"]):
            is_feminine = True
            is_plural = True
        elif any(token in m for token in ["gousse", "tasse", "once", "livre", "pincée"]):
            is_feminine = True
            is_plural = False

        lower_name = n.lower()
        stems = {
            "éminc": ("émincé", "émincée", "émincés", "émincées"),
            "hach": ("haché", "hachée", "hachés", "hachées"),
            "tranch": ("tranché", "tranchée", "tranchés", "tranchées"),
            "râp": ("râpé", "râpée", "râpés", "râpées"),
            "écras": ("écrasé", "écrasée", "écrasés", "écrasées"),
        }

        if is_feminine and is_plural:
            form_idx = 3
        elif is_feminine:
            form_idx = 1
        elif is_plural:
            form_idx = 2
        else:
            form_idx = 0

        import re
        for stem, forms in stems.items():
            pattern = rf" ({re.escape(stem)})(é|ée|és|ées)$"
            if re.search(pattern, lower_name):
                target = forms[form_idx]
                return re.sub(pattern, f" {target}", n, flags=re.IGNORECASE)
        return n

    def _naturalize_french_ingredient(name_fr: str) -> str:
        import re
        n = (name_fr or "").strip()
        if not n:
            return n

        n = re.sub(r"\s+", " ", n)
        n = re.sub(r"\bd\'\s+", "d'", n)
        n = re.sub(r"\bde\s+de\b", "de", n)
        n = re.sub(r"\bd'\s+d'", "d'", n)
        n = re.sub(r"\bde\s+d'", "d'", n)
        return n.strip(" ,.-")

    def _maybe_singularize_by_quantity(name_fr: str, measure_fr: str) -> str:
        import re
        from fractions import Fraction

        n = (name_fr or "").strip()
        m = (measure_fr or "").strip().lower()
        if not n or not m:
            return n

        qty_match = re.match(r"^([\d.,/\s]+)", m)
        if not qty_match:
            return n

        qty_raw = qty_match.group(1).strip()
        try:
            if ' ' in qty_raw and '/' in qty_raw:
                main, frac = qty_raw.split(' ', 1)
                qty = float(main) + float(Fraction(frac))
            elif '/' in qty_raw:
                qty = float(Fraction(qty_raw))
            else:
                qty = float(qty_raw.replace(',', '.'))
        except Exception:
            return n

        if abs(qty - 1.0) > 0.0001:
            return n

        # Isoler le noyau nominal (avant éventuel qualificatif final)
        words = n.split()
        if not words:
            return n

        idx = 0
        if words[0].lower() in {"de", "d'"} and len(words) > 1:
            idx = 1

        first = words[idx]
        lower_first = first.lower()

        irregular = {
            "oeufs": "oeuf",
            "œufs": "œuf",
            "oignons": "oignon",
            "carottes": "carotte",
            "tomates": "tomate",
            "pommes": "pomme",
            "gousses": "gousse",
        }
        invariants = {"couscous", "maïs", "pois", "radis", "anis"}

        if lower_first in invariants:
            return n

        if lower_first in irregular:
            words[idx] = irregular[lower_first]
            return " ".join(words)

        if lower_first.endswith("s") and len(lower_first) > 3:
            words[idx] = first[:-1]
            return " ".join(words)

        return n

    for i in range(1, 21):
        ing_en = (meal.get(f"strIngredient{i}") or "").strip()
        measure_en = (meal.get(f"strMeasure{i}") or "").strip()
        
        if not ing_en:
            continue
        
        ing_work = ing_en
        measure_work = measure_en

        # Certains flux TheMealDB mettent "chopped/minced/..." dans la mesure.
        # On le déplace vers l'ingrédient pour obtenir "oignons hachés" au lieu de "2 haché oignons".
        measure_lower = measure_work.lower()
        for prep in prep_terms:
            if re.search(rf"\b{re.escape(prep)}\b", measure_lower):
                if prep not in ing_work.lower():
                    ing_work = f"{prep} {ing_work}".strip()
                measure_work = re.sub(rf"\b{re.escape(prep)}\b", "", measure_work, flags=re.IGNORECASE)
                measure_work = re.sub(r"\s+", " ", measure_work).strip(" ,.-")
                measure_lower = measure_work.lower()

        # Traduire le nom de l'ingrédient
        ing_fr = _translate_ingredient_name(ing_work)
        
        # Adapter et traduire la mesure
        measure_fr = _adapt_and_translate_measure(measure_work, ratio)
        
        # Pour un rendu FR naturel: "2 c. à soupe de beurre", "4 quarts de bouillon"
        if _needs_de_prefix(measure_fr):
            ing_fr = _add_de_prefix(ing_fr)

        ing_fr = _maybe_singularize_by_quantity(ing_fr, measure_fr)
        ing_fr = _agree_prep_with_measure(ing_fr, measure_fr)
        ing_fr = _naturalize_french_ingredient(ing_fr)

        ingredients.append({"name": ing_fr, "measure": measure_fr})
        all_ingredients_lower.append(ing_en.lower())
    
    # Extraire les tags
    tags = []
    if meal.get("strTags"):
        tags = [t.strip() for t in meal["strTags"].split(",")]
    if meal.get("strCategory"):
        tags.append(meal["strCategory"])
    
    # Détecter les régimes alimentaires
    diet_tags = _detect_diet_tags(meal, all_ingredients_lower)
    
    return {
        "title": meal.get("strMeal", ""),
        "ingredients_json": json.dumps(ingredients),
        "instructions": meal.get("strInstructions", ""),
        "prep_time": 30,
        "cook_time": 30,
        "servings": target_servings,
        "source_url": meal.get("strSource", ""),
        "image_url": meal.get("strMealThumb", ""),
        "tags_json": json.dumps(tags),
        "diet_tags_json": json.dumps(diet_tags),
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
        "lactose": ["milk", "cream", "cheese", "butter", "lait", "crème", "fromage", "beurre",
                     "mozzarella", "ricotta", "parmesan", "emmental", "camembert", "comté", 
                     "chèvre", "roquefort", "crème fraîche", "yaourt", "yogurt"],
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
            "pancetta", "prosciutto", "salami", "oxtail", "queue",
            "steak haché", "ground beef", "hachis", "salmon", "saumon", "tuna", "thon",
            "shrimp", "crevette", "crevettes", "crabe", "crab", "lobster", "homard",
            "mussel", "moule", "moules", "huître", "oyster", "seiche", "calamar",
            "mollusque", "fruits de mer", "seafood", "squid", "poulpe",
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
            # Crustacés et mollusques
            "shrimp", "crevette", "crevettes", "crabe", "crab", "lobster", "homard",
            "mussel", "moule", "moules", "huître", "oyster", "seiche", "calamar",
            "mollusque", "fruits de mer", "seafood",
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
            "steak", "gibier", "oxtail", "queue",
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
