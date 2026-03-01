#!/usr/bin/env python3
"""
Script de test pour déboguer le endpoint /api/recipes/suggest
"""
import json
import sys
sys.path.insert(0, "c:\\Users\\natah\\Desktop\\FrigoScan")

from server.services.recipe_service import load_local_recipes, compute_match_score

# Test 1: Charger les recettes
print("=" * 60)
print("Test 1: Charger les recettes locales")
print("=" * 60)
recipes = load_local_recipes()
print(f"✓ Total recettes chargées: {len(recipes)}")

if len(recipes) > 0:
    print(f"\nPremière recette:")
    first = recipes[0]
    print(f"  - Titre: {first.get('title')}")
    print(f"  - Ingrédients JSON: {first.get('ingredients_json')[:100]}...")
    print(f"  - Instructions: {first.get('instructions')[:100]}...")
    print(f"  - Temps prep: {first.get('prep_time')}")
    print(f"  - Temps cuisson: {first.get('cook_time')}")
    
    # Lister les sources
    marmiton_count = sum(1 for r in recipes if "Ratatouille" not in r.get('title', ''))
    print(f"\nRécapitulatif:")
    print(f"  - Recettes chargées: {len(recipes)}")

# Test 2: Tester compute_match_score
print("\n" + "=" * 60)
print("Test 2: Tester le calcul du score")
print("=" * 60)

if len(recipes) > 0:
    first_recipe = recipes[0]
    ingredients_json = first_recipe.get("ingredients_json", "[]")
    
    # Simuler un frigo avec quelques ingrédients
    fridge_items = [
        {"name": "tomate", "status": "active"},
        {"name": "oignon", "status": "active"},
        {"name": "ail", "status": "active"},
        {"name": "huile d'olive", "status": "active"},
        {"name": "sel", "status": "active"},
    ]
    
    print(f"Recette: {first_recipe.get('title')}")
    print(f"Frigo contient: {', '.join([item['name'] for item in fridge_items])}")
    
    score, missing = compute_match_score(ingredients_json, fridge_items)
    print(f"\nRésultat:")
    print(f"  - Score: {score}%")
    print(f"  - Ingrédients manquants: {missing[:5]}...")

# Test 3: Analyser la distribution des scores
print("\n" + "=" * 60)
print("Test 3: Distribution des scores avec frigo complet")
print("=" * 60)

fridge_items = [
    {"name": "tomate", "status": "active"},
    {"name": "courgette", "status": "active"},
    {"name": "aubergine", "status": "active"},
    {"name": "poivron", "status": "active"},
    {"name": "oignon", "status": "active"},
    {"name": "ail", "status": "active"},
    {"name": "huile d'olive", "status": "active"},
    {"name": "thym", "status": "active"},
    {"name": "sel", "status": "active"},
    {"name": "poivre", "status": "active"},
    {"name": "pâtes", "status": "active"},
    {"name": "fromage", "status": "active"},
    {"name": "champignons", "status": "active"},
    {"name": "lait", "status": "active"},
    {"name": "œuf", "status": "active"},
]

scores = []
for recipe in recipes[:15]:
    recipe_ings = recipe.get("ingredients_json", "[]")
    score, _ = compute_match_score(recipe_ings, fridge_items)
    scores.append((recipe.get("title"), score))

scores.sort(key=lambda x: x[1], reverse=True)
print(f"Top 10 recettes avec le frigo fourni:")
for title, score in scores[:10]:
    print(f"  - {title}: {score}%")

print(f"\nRécapitulatif des scores:")
print(f"  - Moyenne: {sum(s[1] for s in scores) / len(scores):.1f}%")
print(f"  - Min: {min(s[1] for s in scores):.1f}%")
print(f"  - Max: {max(s[1] for s in scores):.1f}%")
print(f"  - >= 20%: {sum(1 for s in scores if s[1] >= 20)}")
print(f"  - >= 50%: {sum(1 for s in scores if s[1] >= 50)}")

print("\n✓ Test complété avec succès!")
