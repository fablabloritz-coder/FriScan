#!/usr/bin/env python3
"""
Test endpoint /api/recipes/suggest
"""
import json
import requests
import sqlite3

BASE_URL = "http://localhost:8001"

# Vérifier d'abord le contenu du frigo dans la BD
print("=" * 60)
print("Contenu du frigo (depuis BD)")
print("=" * 60)

db = sqlite3.connect("c:\\Users\\natah\\Desktop\\FrigoScan\\server\\data\\frigoscan.db")
db.row_factory = sqlite3.Row
fridge = db.execute("SELECT * FROM fridge_items WHERE status='active'").fetchall()
print(f"Total actifs: {len(fridge)}")
for item in fridge[:10]:
    print(f"  - {item['name']} (expire: {item['expiry_date'] if 'expiry_date' in item.keys() else 'N/A'})")
if len(fridge) > 10:
    print(f"  ... et {len(fridge) - 10} de plus")
db.close()

# Test le endpoint
print("\n" + "=" * 60)
print("Test: GET /api/recipes/suggest")
print("=" * 60)

response = requests.get(f"{BASE_URL}/api/recipes/suggest", params={
    "max_results": 10,
    "min_score": 20.0
})

print(f"Status code: {response.status_code}")
data = response.json()

if data.get("success"):
    recipes = data.get("recipes", [])
    print(f"Recettes retournées: {len(recipes)}")
    
    if recipes:
        print("\nTop recettes:")
        for i, recipe in enumerate(recipes[:5], 1):
            print(f"\n  {i}. {recipe.get('title')}")
            print(f"     Score: {recipe.get('match_score', 'N/A')}%")
            print(f"     Ingrédients manquants: {len(recipe.get('missing_ingredients', []))}")
            if recipe.get('missing_ingredients'):
                print(f"       {', '.join(recipe['missing_ingredients'][:3])}")
    else:
        print("Aucune recette trouvée!")
        print(f"Message: {data.get('message', 'N/A')}")
else:
    print(f"Erreur: {data}")

# Test aussi la liste complète de recettes
print("\n" + "=" * 60)
print("Test: GET /api/recipes/")
print("=" * 60)

response = requests.get(f"{BASE_URL}/api/recipes/")
data = response.json()
print(f"Recettes totales en BD: {len(data.get('recipes', []))}")

# Test /categories
print("\n" + "=" * 60)
print("Test: GET /api/recipes/categories")
print("=" * 60)

response = requests.get(f"{BASE_URL}/api/recipes/categories")
data = response.json()
if data.get("success"):
    categories = data.get("categories", [])
    print(f"Catégories: {len(categories)}")
    print(f"Exemples: {', '.join(categories[:5])}")
else:
    print(f"Erreur: {data}")

print("\n✓ Test complété!")
