#!/usr/bin/env python3
"""
Audit complet de tous les endpoints FrigoScan
Vérifie les incohérences de nommage entre backend et frontend
"""
import requests
import json

BASE_URL = "http://localhost:8001"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def test_endpoint(name, url, expected_keys):
    """Teste un endpoint et vérifie les clés retournées"""
    print(f"\n{BLUE}Testing:{RESET} {name}")
    print(f"  URL: {url}")
    
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            print(f"  {RED}✗ Status: {resp.status_code}{RESET}")
            return False
        
        data = resp.json()
        actual_keys = set(data.keys())
        expected_set = set(expected_keys)
        
        # Vérifier success
        if "success" in data:
            if data["success"]:
                print(f"  {GREEN}✓ success: True{RESET}")
            else:
                print(f"  {RED}✗ success: False{RESET}")
        
        # Vérifier les clés attendues
        missing = expected_set - actual_keys
        extra = actual_keys - expected_set
        
        if not missing and not extra:
            print(f"  {GREEN}✓ Toutes les clés attendues présentes{RESET}")
            return True
        else:
            if missing:
                print(f"  {RED}✗ Clés manquantes: {missing}{RESET}")
            if extra:
                print(f"  {YELLOW}⚠ Clés supplémentaires: {extra}{RESET}")
            return False
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        return False

def check_frontend_calls(js_file, endpoint_pattern):
    """Vérifie comment le frontend appelle les variables"""
    print(f"\n{BLUE}Checking frontend:{RESET} {js_file}")
    
    try:
        with open(f"c:\\Users\\natah\\Desktop\\FrigoScan\\static\\js\\{js_file}", "r", encoding="utf-8") as f:
            content = f.read()
            
        # Chercher les patterns data.items, data.recipes, etc.
        patterns = [
            ("data.items", "items"),
            ("data.data", "data"),
            ("data.recipes", "recipes"),
            ("data.menus", "menus"),
            ("data.stats", "stats"),
            ("data.categories", "categories"),
        ]
        
        found = []
        for pattern, key in patterns:
            if pattern in content:
                occurrences = content.count(pattern)
                found.append((pattern, occurrences))
                print(f"  {YELLOW}→{RESET} {pattern}: {occurrences} occurrence(s)")
        
        if not found:
            print(f"  {GREEN}✓ Aucun pattern data.* détecté{RESET}")
        
        return found
    except Exception as e:
        print(f"  {RED}✗ Erreur lecture: {e}{RESET}")
        return []

print("=" * 80)
print(f"{BLUE}AUDIT COMPLET FRIGOSCAN - ENDPOINTS{RESET}")
print("=" * 80)

# Test des endpoints principaux
results = []

print(f"\n{YELLOW}[FRIGO ENDPOINTS]{RESET}")
results.append(test_endpoint(
    "GET /api/fridge/",
    f"{BASE_URL}/api/fridge/",
    ["success", "items", "page", "limit", "total", "pages", "count"]
))

print(f"\n{YELLOW}[RECIPES ENDPOINTS]{RESET}")
results.append(test_endpoint(
    "GET /api/recipes/",
    f"{BASE_URL}/api/recipes/",
    ["success", "recipes"]
))
results.append(test_endpoint(
    "GET /api/recipes/suggest",
    f"{BASE_URL}/api/recipes/suggest",
    ["success", "recipes"]
))
results.append(test_endpoint(
    "GET /api/recipes/categories",
    f"{BASE_URL}/api/recipes/categories",
    ["success", "categories"]
))

print(f"\n{YELLOW}[MENUS ENDPOINTS]{RESET}")
results.append(test_endpoint(
    "GET /api/menus/",
    f"{BASE_URL}/api/menus/",
    ["success", "menus"]
))

print(f"\n{YELLOW}[SHOPPING ENDPOINTS]{RESET}")
results.append(test_endpoint(
    "GET /api/shopping/",
    f"{BASE_URL}/api/shopping/",
    ["success", "items", "count"]
))

print(f"\n{YELLOW}[STATS ENDPOINTS]{RESET}")
results.append(test_endpoint(
    "GET /api/fridge/stats/summary",
    f"{BASE_URL}/api/fridge/stats/summary",
    ["success", "stats"]
))

# Audit frontend
print("\n" + "=" * 80)
print(f"{BLUE}AUDIT FRONTEND - APPELS API{RESET}")
print("=" * 80)

frontend_files = [
    "fridge.js",
    "recipes.js",
    "menus.js",
    "shopping.js",
    "stats.js",
    "scanner.js",
    "manual-add.js",
]

for js_file in frontend_files:
    check_frontend_calls(js_file, "data.")

# Résumé
print("\n" + "=" * 80)
print(f"{BLUE}RÉSUMÉ{RESET}")
print("=" * 80)

passed = sum(1 for r in results if r)
total = len(results)

print(f"\nEndpoints testés: {total}")
print(f"✓ Conformes: {GREEN}{passed}{RESET}")
print(f"✗ Non conformes: {RED}{total - passed}{RESET}")

if passed == total:
    print(f"\n{GREEN}✓ TOUS LES ENDPOINTS SONT CONFORMES!{RESET}")
else:
    print(f"\n{YELLOW}⚠ {total - passed} endpoint(s) nécessitent une correction{RESET}")

print("\n" + "=" * 80)
