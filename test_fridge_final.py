#!/usr/bin/env python3
"""
Test final du frigo - Simulation complète
"""
import requests
import json

BASE_URL = "http://localhost:8001"

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def test(name, condition):
    if condition:
        print(f"{GREEN}✓{RESET} {name}")
        return True
    else:
        print(f"{RED}✗{RESET} {name}")
        return False

print("="*60)
print("TEST FINAL - FRIGO COMPLET")
print("="*60)

results = []

# Test 1: Récupérer la liste
print("\n1. GET /api/fridge/ (récupérer liste)")
resp = requests.get(f"{BASE_URL}/api/fridge/")
data = resp.json()
results.append(test("Status 200", resp.status_code == 200))
results.append(test("success = True", data.get("success") == True))
results.append(test("Clé 'items' existe", "items" in data))
results.append(test("items est une liste", isinstance(data.get("items"), list)))
initial_count = len(data.get("items", []))
print(f"  → {initial_count} items dans le frigo")

# Test 2: Ajouter un item
print("\n2. POST /api/fridge/ (ajouter un item)")
new_item = {
    "name": "Test Item",
    "category": "test",
    "quantity": 1.0,
    "unit": "unité",
    "dlc": "2026-03-10"
}
resp = requests.post(f"{BASE_URL}/api/fridge/", json=new_item)
data = resp.json()
results.append(test("Status 200", resp.status_code == 200))
results.append(test("success = True", data.get("success") == True))
results.append(test("item retourné", "item" in data))
new_id = data.get("item", {}).get("id")
print(f"  → Item ajouté avec ID: {new_id}")

# Test 3: Vérifier l'ajout
print("\n3. GET /api/fridge/ (vérifier l'ajout)")
resp = requests.get(f"{BASE_URL}/api/fridge/")
data = resp.json()
new_count = len(data.get("items", []))
results.append(test("Count augmenté de 1", new_count == initial_count + 1))
print(f"  → {new_count} items maintenant ({new_count - initial_count} ajouté)")

# Test 4: Filtres
print("\n4. GET /api/fridge/?filter_dlc=soon")
resp = requests.get(f"{BASE_URL}/api/fridge/?filter_dlc=soon")
data = resp.json()
results.append(test("Filtre soon fonctionne", resp.status_code == 200))
print(f"  → {len(data.get('items', []))} items bientôt périmés")

print("\n5. GET /api/fridge/?sort=category")
resp = requests.get(f"{BASE_URL}/api/fridge/?sort=category")
data = resp.json()
results.append(test("Tri par catégorie fonctionne", resp.status_code == 200))

# Test 5: Consommer l'item
if new_id:
    print(f"\n6. POST /api/fridge/{new_id}/consume")
    resp = requests.post(f"{BASE_URL}/api/fridge/{new_id}/consume?user_name=Test")
    data = resp.json()
    results.append(test("Consommation réussie", data.get("success") == True))

# Test 6: Supprimer l'item
if new_id:
    print(f"\n7. DELETE /api/fridge/{new_id}")
    resp = requests.delete(f"{BASE_URL}/api/fridge/{new_id}")
    data = resp.json()
    results.append(test("Suppression réussie", data.get("success") == True))

# Test 7: Vérifier la suppression
print("\n8. GET /api/fridge/ (vérifier suppression)")
resp = requests.get(f"{BASE_URL}/api/fridge/")
data = resp.json()
final_count = len(data.get("items", []))
results.append(test("Item supprimé", final_count == initial_count))
print(f"  → {final_count} items (retour au count initial)")

# Résumé
print("\n" + "="*60)
print("RÉSUMÉ")
print("="*60)
passed = sum(results)
total = len(results)
print(f"\nTests: {passed}/{total} réussis ({passed*100//total}%)")

if passed == total:
    print(f"\n{GREEN}✓ TOUS LES TESTS PASSÉS! LE FRIGO FONCTIONNE PARFAITEMENT{RESET}")
else:
    print(f"\n{RED}✗ {total-passed} test(s) échoué(s){RESET}")
