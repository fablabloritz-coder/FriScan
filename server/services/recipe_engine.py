"""
FriScan — Moteur de suggestions de recettes (v2)
Matching intelligent avec synonymes, gestion pluriel/singulier,
et distinction entre produits similaires (pâtes ≠ pâte brisée).
"""
import json
import os
import unicodedata
import re
from difflib import SequenceMatcher
from server.models import RecipeSuggestion


RECIPES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "recipes.json")

# ─────────────────────── SYNONYMES / GROUPES D'INGRÉDIENTS ───────────────────
# Chaque groupe = ensemble de termes qui désignent LE MÊME produit.
SYNONYM_GROUPS: list[set[str]] = [
    {"pates", "spaghetti", "spaghettis", "tagliatelles", "penne", "fusilli",
     "macaroni", "nouilles", "coquillettes", "farfalle", "linguine"},
    {"pate brisee", "pate feuilletee", "pate sablee", "pate a tarte"},
    {"tomate", "tomates", "tomates cerises", "tomates pelees",
     "coulis de tomate", "sauce tomate"},
    {"poulet", "blanc de poulet", "escalope de poulet", "cuisse de poulet",
     "filet de poulet"},
    {"boeuf", "steak", "viande hachee", "steak hache"},
    {"porc", "cotes de porc", "echine de porc", "filet mignon"},
    {"saumon", "pave de saumon", "filet de saumon", "saumon fume"},
    {"pomme de terre", "pommes de terre", "patate", "patates"},
    {"pomme", "pommes"},
    {"oignon", "oignons", "echalote", "echalotes"},
    {"ail", "gousse d'ail", "gousses d'ail"},
    {"carotte", "carottes"},
    {"courgette", "courgettes"},
    {"aubergine", "aubergines"},
    {"poivron", "poivrons"},
    {"champignon", "champignons", "champignons de paris"},
    {"haricot vert", "haricots verts"},
    {"petit pois", "petits pois"},
    {"poireau", "poireaux"},
    {"salade", "laitue", "batavia", "feuille de chene"},
    {"fromage", "emmental", "gruyere", "comte", "fromage rape"},
    {"mozzarella", "mozzarelle"},
    {"parmesan", "parmigiano"},
    {"creme fraiche", "creme", "creme liquide", "creme epaisse"},
    {"lait", "lait entier", "lait demi-ecreme"},
    {"beurre"},
    {"oeuf", "oeufs"},
    {"huile d'olive", "huile olive"},
    {"huile", "huile de tournesol", "huile vegetale"},
    {"riz", "riz basmati", "riz long", "riz complet"},
    {"pain", "pain de mie", "baguette"},
    {"farine", "farine de ble"},
    {"sucre", "sucre en poudre", "sucre roux"},
    {"sel", "sel fin", "gros sel"},
    {"poivre", "poivre noir", "poivre moulu"},
    {"basilic", "basilic frais"},
    {"persil", "persil frais", "persil plat"},
    {"thym", "thym frais"},
    {"romarin", "romarin frais"},
    {"cannelle", "cannelle en poudre"},
    {"jambon", "jambon blanc", "jambon cru"},
    {"lardons", "lardon", "poitrine fumee"},
    {"yaourt", "yogourt", "yaourt nature", "sauce yaourt"},
    {"banane", "bananes"},
    {"fraise", "fraises"},
    {"framboise", "framboises"},
    {"citron", "citrons", "jus de citron"},
    {"orange", "oranges", "jus d'orange"},
    {"avocat", "avocats"},
    {"concombre", "concombres"},
    {"mais", "mais en boite"},
    {"olive", "olives", "olives noires"},
    {"noix", "cerneaux de noix"},
    {"miel"},
    {"moutarde", "moutarde de dijon"},
    {"vinaigre", "vinaigre balsamique", "vinaigre de vin"},
    {"sauce soja", "sauce soja sucree"},
    {"bouillon", "bouillon de volaille", "bouillon de legumes", "bouillon cube"},
    {"vin blanc", "vin blanc sec"},
    {"tortilla", "tortillas", "galette de ble"},
    {"chevre", "fromage de chevre", "buche de chevre"},
    {"levure", "levure de boulanger", "levure seche"},
]

# Index inversé : mot normalisé → index du groupe
_SYNONYM_INDEX: dict[str, int] = {}
for _i, _group in enumerate(SYNONYM_GROUPS):
    for _term in _group:
        _SYNONYM_INDEX[_term] = _i


# ─────────── PRODUITS QUI NE DOIVENT PAS MATCHER ENTRE EUX ───────────────────
EXCLUSION_PAIRS: list[tuple[str, str]] = [
    ("pates", "pate brisee"),
    ("pates", "pate feuilletee"),
    ("pates", "pate sablee"),
    ("pates", "pate a tarte"),
    ("pate", "pate brisee"),
    ("pate", "pate feuilletee"),
    ("pate", "pate sablee"),
    ("pomme", "pomme de terre"),
    ("pommes", "pommes de terre"),
]

_EXCLUSION_SET: set[tuple[str, str]] = set()
for _a, _b in EXCLUSION_PAIRS:
    _EXCLUSION_SET.add((_a, _b))
    _EXCLUSION_SET.add((_b, _a))


# ─────────────────────── NORMALISATION ───────────────────────────────────────

def _remove_accents(text: str) -> str:
    """Supprime les accents d'un texte."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize(text: str) -> str:
    """Normalise : minuscules, sans accents, sans articles."""
    t = text.lower().strip()
    t = _remove_accents(t)
    t = re.sub(r"^(le |la |les |l'|du |de la |des |de |d'|un |une )", "", t)
    return t.strip()


def _get_root_words(text: str) -> set[str]:
    """Extrait les mots-racines significatifs d'un texte normalisé."""
    stop_words = {"de", "du", "la", "le", "les", "l", "d", "a", "au", "aux",
                  "en", "et", "un", "une", "des"}
    words = re.split(r"[\s'\-]+", text)
    return {w for w in words if w and w not in stop_words and len(w) > 1}


def _singularize(word: str) -> str:
    """Simple singularisation du français."""
    if word.endswith("aux") and len(word) > 4:
        return word[:-3] + "al"
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


# ─────────────────────── MATCHING ──────────────────────────────────────────

def _is_excluded(fi: str, ri: str) -> bool:
    """Vérifie si la paire est dans les exclusions (directe ou composante)."""
    if (fi, ri) in _EXCLUSION_SET:
        return True
    fi_s = _singularize(fi)
    ri_s = _singularize(ri)
    if (fi_s, ri_s) in _EXCLUSION_SET:
        return True
    for (ea, eb) in _EXCLUSION_SET:
        if (ea == fi or ea == fi_s) and (eb == ri or eb == ri_s):
            return True
        if (eb == fi or eb == fi_s) and (ea == ri or ea == ri_s):
            return True
    return False


def _ingredient_match(fridge_item: str, recipe_ingredient: str) -> bool:
    """
    Vérifie si un produit du frigo correspond à un ingrédient de recette.
    Pipeline : exact → singulier → exclusions → synonymes → mots-racines → flou.
    """
    fi = _normalize(fridge_item)
    ri = _normalize(recipe_ingredient)

    # 1. Correspondance exacte
    if fi == ri:
        return True

    # 2. Singularisation
    fi_s = _singularize(fi)
    ri_s = _singularize(ri)
    if fi_s == ri_s:
        return True

    # 3. Exclusions (faux positifs connus)
    if _is_excluded(fi, ri):
        return False

    # 4. Synonymes : même groupe ?
    fi_group = _SYNONYM_INDEX.get(fi) or _SYNONYM_INDEX.get(fi_s)
    ri_group = _SYNONYM_INDEX.get(ri) or _SYNONYM_INDEX.get(ri_s)

    if fi_group is not None and ri_group is not None:
        return fi_group == ri_group
    if fi_group is not None:
        group = SYNONYM_GROUPS[fi_group]
        if ri in group or ri_s in group:
            return True
    if ri_group is not None:
        group = SYNONYM_GROUPS[ri_group]
        if fi in group or fi_s in group:
            return True

    # 5. Matching par mots-racines
    fi_words = _get_root_words(fi)
    ri_words = _get_root_words(ri)
    fi_words_s = {_singularize(w) for w in fi_words}
    ri_words_s = {_singularize(w) for w in ri_words}

    # Mot simple du frigo présent dans ingrédient composé (max 3 mots)
    if len(fi_words) == 1 and fi_words_s:
        main_word = next(iter(fi_words_s))
        if main_word in ri_words_s and len(ri_words) <= 3:
            return True

    # Ingrédient recette = mot simple, présent dans nom du produit
    if len(ri_words) == 1 and ri_words_s:
        main_word = next(iter(ri_words_s))
        if main_word in fi_words_s:
            return True

    # 6. Correspondance floue (seuil élevé = 0.82 pour éviter faux positifs)
    ratio = SequenceMatcher(None, fi_s, ri_s).ratio()
    if ratio >= 0.82:
        return True

    return False


# ─────────────────────── CHARGEMENT RECETTES ─────────────────────────────────

def load_recipes() -> list[dict]:
    """Charge la base de recettes depuis le fichier JSON."""
    try:
        with open(RECIPES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# ─────────────────────── SUGGESTION ──────────────────────────────────────────

def suggest_recipes(
    fridge_products: list[str],
    max_results: int = 10,
    min_match_ratio: float = 0.3,
    prioritize_expiring: list[str] | None = None,
) -> list[RecipeSuggestion]:
    """
    Suggère des recettes en fonction des produits du frigo.

    Args:
        fridge_products: Liste des noms de produits dans le frigo.
        max_results: Nombre maximum de suggestions.
        min_match_ratio: Ratio minimum d'ingrédients trouvés.
        prioritize_expiring: Produits proches de la péremption (bonus de score).

    Returns:
        Liste de RecipeSuggestion triée par pertinence.
    """
    recipes = load_recipes()
    if not recipes or not fridge_products:
        return []

    expiring_set = set(_normalize(p) for p in (prioritize_expiring or []))
    suggestions = []

    for recipe in recipes:
        recipe_ingredients = recipe.get("ingredients", [])
        if not recipe_ingredients:
            continue

        matched = []
        missing = []

        for ingredient in recipe_ingredients:
            found = False
            for fridge_item in fridge_products:
                if _ingredient_match(fridge_item, ingredient):
                    matched.append(ingredient)
                    found = True
                    break
            if not found:
                missing.append(ingredient)

        if not matched:
            continue

        # Calcul du score
        base_score = len(matched) / len(recipe_ingredients)

        # Bonus si on utilise des produits proches de la péremption
        expiry_bonus = 0.0
        if expiring_set:
            for m in matched:
                for exp in expiring_set:
                    if _ingredient_match(exp, m):
                        expiry_bonus += 0.1
                        break
            expiry_bonus = min(expiry_bonus, 0.2)  # plafond à 0.2

        final_score = min(base_score + expiry_bonus, 1.0)

        if final_score >= min_match_ratio:
            suggestions.append(RecipeSuggestion(
                name=recipe.get("name", "Recette sans nom"),
                ingredients=recipe_ingredients,
                matched_ingredients=matched,
                missing_ingredients=missing,
                match_score=round(final_score, 2),
                instructions=recipe.get("instructions", ""),
                prep_time=recipe.get("prep_time"),
                servings=recipe.get("servings"),
                image_url=recipe.get("image_url"),
            ))

    # Trier par score décroissant, puis par nombre d'ingrédients manquants
    suggestions.sort(key=lambda s: (-s.match_score, len(s.missing_ingredients)))

    return suggestions[:max_results]
