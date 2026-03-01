#!/usr/bin/env python3
"""
Suite de tests complète pour tous les endpoints FrigoScan
"""
import requests
import json

BASE_URL = "http://localhost:8001"

# Couleurs pour l'output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def test_endpoint(method, endpoint, params=None, data=None, expected_status=200):
    """Helper pour tester un endpoint"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            resp = requests.get(url, params=params, timeout=5)
        elif method.upper() == "POST":
            resp = requests.post(url, json=data, timeout=5)
        else:
            resp = requests.request(method, url, json=data, timeout=5)
        
        success = resp.status_code == expected_status
        status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        print(f"{status} {method:4} {endpoint:40} → {resp.status_code}")
        
        return success, resp
    except Exception as e:
        print(f"{RED}✗{RESET} {method:4} {endpoint:40} → Error: {str(e)[:50]}")
        return False, None

# Tests
print("\n" + "="*80)
print("TESTS ENDPOINTS FRIGOSCAN")
print("="*80)

results = []

# === RECIPES ENDPOINTS ===
print(f"\n{YELLOW}[RECETTES]{RESET}")

ok, resp = test_endpoint("GET", "/api/recipes/", expected_status=200)
results.append(("GET /api/recipes/", ok))
if resp:
    count = len(resp.json().get("recipes", []))
    print(f"  → Contient {count} recettes")

ok, resp = test_endpoint("GET", "/api/recipes/search", params={"q": "salade"}, expected_status=200)
results.append(("GET /api/recipes/search", ok))
if resp and resp.json().get("success"):
    count = len(resp.json().get("recipes", []))
    print(f"  → Trouvé {count} recettes pour 'salade'")

ok, resp = test_endpoint("GET", "/api/recipes/suggest", params={"max_results": 10}, expected_status=200)
results.append(("GET /api/recipes/suggest", ok))
if resp and resp.json().get("success"):
    count = len(resp.json().get("recipes", []))
    print(f"  → Retourné {count} recettes suggérées")

ok, resp = test_endpoint("GET", "/api/recipes/suggest/random", params={"count": 5}, expected_status=200)
results.append(("GET /api/recipes/suggest/random", ok))
if resp and resp.json().get("success"):
    count = len(resp.json().get("recipes", []))
    print(f"  → Retourné {count} recettes aléatoires")

ok, resp = test_endpoint("GET", "/api/recipes/categories", expected_status=200)
results.append(("GET /api/recipes/categories", ok))
if resp and resp.json().get("success"):
    count = len(resp.json().get("categories", []))
    print(f"  → {count} catégories disponibles")

# === MENUS ENDPOINTS ===
print(f"\n{YELLOW}[MENUS]{RESET}")

ok, resp = test_endpoint("GET", "/api/menus/", expected_status=200)
results.append(("GET /api/menus/", ok))
if resp:
    data = resp.json()
    count = len(data.get("menus", []))
    print(f"  → {count} menus en BD")

ok, resp = test_endpoint("POST", "/api/menus/generate", 
                        data={"week_start": "2025-01-06"}, expected_status=200)
results.append(("POST /api/menus/generate", ok))
if resp and resp.json().get("success"):
    count = len(resp.json().get("menu_items", []))
    print(f"  → Généré {count} items de menu")

# === FRIDGE ENDPOINTS ===
print(f"\n{YELLOW}[FRIGO]{RESET}")

ok, resp = test_endpoint("GET", "/api/fridge/", expected_status=200)
results.append(("GET /api/fridge/", ok))
if resp:
    count = len(resp.json().get("items", []))
    print(f"  → {count} items dans le frigo")

ok, resp = test_endpoint("POST", "/api/fridge/", 
                        data={"name": "Test Item", "quantity": 1}, expected_status=201)
results.append(("POST /api/fridge/", ok))
if resp and resp.json().get("success"):
    item_id = resp.json().get("item", {}).get("id")
    print(f"  → Ajouté item {item_id}")
    
    # Cleanup: supprimer l'item ajouté
    test_endpoint("DELETE", f"/api/fridge/{item_id}", expected_status=200)

# === SETTINGS ENDPOINTS ===
print(f"\n{YELLOW}[PARAMÈTRES]{RESET}")

ok, resp = test_endpoint("GET", "/api/settings/", expected_status=200)
results.append(("GET /api/settings/", ok))
if resp:
    settings = resp.json().get("settings", {})
    print(f"  → {len(settings)} paramètres")

ok, resp = test_endpoint("GET", "/api/settings/diets", expected_status=200)
results.append(("GET /api/settings/diets", ok))
if resp and resp.json().get("success"):
    print(f"  → Régimes: {resp.json().get('diets', [])}")

ok, resp = test_endpoint("GET", "/api/settings/allergens", expected_status=200)
results.append(("GET /api/settings/allergens", ok))
if resp and resp.json().get("success"):
    print(f"  → Allergènes: {resp.json().get('allergens', [])}")

# === HEALTH CHECK ===
print(f"\n{YELLOW}[SANTÉ]{RESET}")

ok, resp = test_endpoint("GET", "/health", expected_status=200)
results.append(("GET /health", ok))
if resp:
    print(f"  → {resp.json().get('status', 'unknown')}")

# === RÉSUMÉ ===
print("\n" + "="*80)
print("RÉSUMÉ")
print("="*80)

passed = sum(1 for _, ok in results if ok)
total = len(results)

print(f"\nTests réussis: {GREEN}{passed}/{total}{RESET}")
print(f"Taux de réussite: {passed*100//total}%")

if passed == total:
    print(f"\n{GREEN}✓ TOUS LES TESTS PASSÉS!{RESET}")
else:
    print(f"\n{RED}✗ {total - passed} test(s) échoué(s){RESET}")
    failed = [name for name, ok in results if not ok]
    for name in failed:
        print(f"  - {name}")

print("\n" + "="*80)
