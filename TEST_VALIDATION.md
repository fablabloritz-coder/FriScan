# 🧪 SCRIPTS DE TEST & VALIDATION - FrigoScan

**Objectif**: Reproduire et vérifier les problèmes identifiés dans l'audit

---

## 1️⃣ TEST: Vérifier Fuite de Stack Trace

### Script Python

**Fichier à créer**: `tests/test_error_exposure.py`

```python
"""
Test: Vérifier que les erreurs ne révèlent pas la stacktrace
"""
import requests
import os

BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")

def test_error_exposure():
    """Trigger une erreur et vérifier que la stacktrace est masquée."""
    
    # Trigger division by zero ou autre erreur
    resp = requests.get(f"{BASE_URL}/api/recipes/search?q=")  # q vide
    
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    
    # ✅ ACCEPTABLE: Message générique
    # {"error": "Query parameter 'q' must be at least 2 chars"}
    
    # ❌ À ÉVITER: Stack trace exposée
    # {"error": "Traceback (most recent call last):\n  File..."}
    
    data = resp.json()
    
    assert "Traceback" not in str(data), "Stack trace exposée!"
    assert "File \"" not in str(data), "Chemin fichier exposé!"
    assert "raise " not in str(data), "Code Python exposé!"
    
    print("✅ PASS: Stack traces correctement masquées")

if __name__ == "__main__":
    test_error_exposure()
```

**Commande**:
```bash
cd c:\Users\natah\Desktop\FrigoScan
python tests/test_error_exposure.py
```

---

## 2️⃣ TEST: Vérifier Race Conditions

### Script Python

**Fichier à créer**: `tests/test_concurrent_access.py`

```python
"""
Test: Vérifier que les accès concurrent ne cassent pas la BD
"""
import threading
import requests
import json
import os
from datetime import datetime

BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")
RESULTS = []
ERRORS = []

def add_fridge_item(item_id):
    """Ajouter un item au frigo."""
    try:
        resp = requests.post(
            f"{BASE_URL}/api/fridge",
            json={
                "name": f"Item {item_id}",
                "quantity": 1,
                "unit": "unité",
                "category": "test"
            },
            timeout=10
        )
        
        if resp.status_code == 200:
            RESULTS.append({
                "item_id": item_id,
                "success": True,
                "response": resp.json()
            })
        else:
            ERRORS.append({
                "item_id": item_id,
                "status": resp.status_code,
                "body": resp.text
            })
    
    except Exception as e:
        ERRORS.append({
            "item_id": item_id,
            "error": str(e)
        })

def test_concurrent_writes():
    """Lance 20 threads simultanés qui ajoutent des items."""
    
    print("🧪 Lancement de 20 écritures concurrentes...")
    
    threads = []
    for i in range(20):
        t = threading.Thread(target=add_fridge_item, args=(i,))
        threads.append(t)
        t.start()
    
    # Attendre que tout finisse
    for t in threads:
        t.join()
    
    print(f"\n📊 Résultats:")
    print(f"  ✅ Succès: {len(RESULTS)}")
    print(f"  ❌ Erreurs: {len(ERRORS)}")
    
    if ERRORS:
        print(f"\n⚠️ Erreurs détectées:")
        for err in ERRORS:
            print(f"  - {err}")
    
    # Vérifier qu'on a 20 items (aucune perte de donnée)
    resp = requests.get(f"{BASE_URL}/api/fridge")
    items = resp.json()
    
    # Chercher nos 20 test items
    test_items = [i for i in items if i['name'].startswith('Item')]
    
    print(f"\n✔️ Items créés vérifiés: {len(test_items)}/20")
    
    if len(ERRORS) == 0 and len(test_items) == 20:
        print("✅ PASS: Pas de race conditions détectées")
    else:
        print("❌ FAIL: Race conditions ou perte de données!")

if __name__ == "__main__":
    test_concurrent_writes()
```

**Commande**:
```bash
cd c:\Users\natah\Desktop\FrigoScan
python tests/test_concurrent_access.py
```

---

## 3️⃣ TEST: Vérifier Validation d'Inputs

### Script Python

**Fichier à créer**: `tests/test_input_validation.py`

```python
"""
Test: Vérifier que la validation des inputs est correcte
"""
import requests
import os

BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")

TESTS = [
    # (description, payload, expected_status)
    (
        "Nom vide",
        {"name": "", "quantity": 1},
        400  # Devrait être rejeté
    ),
    (
        "Nom trop long (>200 chars)",
        {"name": "x" * 201, "quantity": 1},
        400
    ),
    (
        "Quantité négative",
        {"name": "Item", "quantity": -5},
        400
    ),
    (
        "Quantité trop grande",
        {"name": "Item", "quantity": 10001},
        400
    ),
    (
        "Format DLC invalide",
        {"name": "Item", "dlc": "2025-13-40"},
        400
    ),
    (
        "Nom avec caractères spéciaux dangereux",
        {"name": "<script>alert('xss')</script>", "quantity": 1},
        400  # Ou peut-être 200 avec sanitization, mais pas XSS!
    ),
    (
        "Nom valide normal",
        {"name": "Lait demi-écrémé", "quantity": 1.5, "dlc": "2025-12-25"},
        200  # Devrait réussir
    ),
]

def test_input_validation():
    """Teste la validation d'input sur chaque cas."""
    
    passed = 0
    failed = 0
    
    for desc, payload, expected_status in TESTS:
        try:
            resp = requests.post(
                f"{BASE_URL}/api/fridge",
                json=payload,
                timeout=5
            )
            
            if resp.status_code == expected_status:
                print(f"✅ {desc}: {resp.status_code}")
                passed += 1
            else:
                print(f"❌ {desc}: Got {resp.status_code}, expected {expected_status}")
                print(f"   Response: {resp.json()}")
                failed += 1
        
        except Exception as e:
            print(f"❌ {desc}: Exception {str(e)}")
            failed += 1
    
    print(f"\n📊 {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ PASS: Validation correcte")
    else:
        print("⚠️ FAIL: Validation incomplète, à corriger!")

if __name__ == "__main__":
    test_input_validation()
```

**Commande**:
```bash
cd c:\Users\natah\Desktop\FrigoScan
python tests/test_input_validation.py
```

---

## 4️⃣ TEST: Vérifier Pagination

### Script Python

**Fichier à créer**: `tests/test_pagination.py`

```python
"""
Test: Vérifier que la pagination fonctionne
"""
import requests
import os

BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")

def test_pagination():
    """Test basic pagination."""
    
    # 1. Vérifier que l'endpoint accepte ?page= et ?limit=
    print("🧪 Test pagination...")
    
    # Page 1 avec limit 10
    resp = requests.get(
        f"{BASE_URL}/api/fridge?page=1&limit=10",
        timeout=5
    )
    
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Response keys: {data.keys()}")
    
    # ✅ ATTENDU:
    # {
    #   "data": [...],
    #   "page": 1,
    #   "limit": 10,
    #   "total": 42,
    #   "pages": 5
    # }
    
    expected_keys = {"data", "page", "limit", "total", "pages"}
    actual_keys = set(data.keys())
    
    if expected_keys.issubset(actual_keys):
        print("✅ PASS: Pagination fields present")
    else:
        print(f"❌ FAIL: Missing keys {expected_keys - actual_keys}")
        print(f"Got: {data}")
    
    # 2. Tester limit invalides
    resp = requests.get(
        f"{BASE_URL}/api/fridge?page=1&limit=1000",  # Trop grand
        timeout=5
    )
    
    if resp.status_code == 400:
        print("✅ PASS: Limite max (500) respectée")
    else:
        print("❌ FAIL: Limite max non appliquée (>500 accepté)")

if __name__ == "__main__":
    test_pagination()
```

**Commande**:
```bash
cd c:\Users\natah\Desktop\FrigoScan
python tests/test_pagination.py
```

---

## 5️⃣ TEST: Vérifier Performance (Indices DB)

### Script Python

**Fichier à créer**: `tests/test_performance.py`

```python
"""
Test: Vérifier que les indices accélèrent les requêtes
"""
import requests
import os
import time

BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")

def test_query_performance():
    """Mesure les temps de requête."""
    
    print("🧪 Test performance requêtes...")
    
    # Requête: Chercher les items avec status='active'
    print("\nTest 1: WHERE status='active'")
    
    start = time.time()
    resp = requests.get(f"{BASE_URL}/api/fridge?status=active", timeout=30)
    elapsed = time.time() - start
    
    print(f"  Temps: {elapsed:.3f}s")
    
    if elapsed < 1.0:
        print("  ✅ PASS: < 1s (indices okay)")
    elif elapsed < 5.0:
        print("  ⚠️  WARNING: 1-5s (peut être accéléré avec indices)")
    else:
        print("  ❌ FAIL: > 5s (indices MANQUANTS!)")
    
    # Requête: Chercher par DLC (expirations)
    print("\nTest 2: WHERE dlc < today")
    
    start = time.time()
    resp = requests.get(f"{BASE_URL}/api/fridge/expiring", timeout=30)
    elapsed = time.time() - start
    
    print(f"  Temps: {elapsed:.3f}s")
    
    if elapsed < 1.0:
        print("  ✅ PASS: < 1s")
    else:
        print("  ⚠️  WARN: > 1s (index sur dlc recommandé)")

if __name__ == "__main__":
    test_query_performance()
```

**Commande**:
```bash
cd c:\Users\natah\Desktop\FrigoScan
python tests/test_performance.py
```

---

## 6️⃣ TEST MANUEL: Import/Export Atomicité

### Instructions

**Objectif**: Vérifier que l'import échoue totalement (rollback) en cas d'erreur

1. **Créer un fichier de test invalide**:

```bash
# Créer `bad_import.json` avec une erreur dans les données
cat > bad_import.json << 'EOF'
{
  "fridge_items": [
    {"name": "Item 1", "quantity": 1},
    {"name": "Item 2", "quantity": "INVALID"},
    {"name": "Item 3", "quantity": 1}
  ]
}
EOF
```

2. **Exporter les données actuelles** (backup):
   - Aller à `Settings → Export → JSON`
   - Sauvegarder le fichier

3. **Essayer d'importer le fichier cassé**:
   - Aller à `Settings → Import → JSON`
   - Importer `bad_import.json`
   - Vérifier: Erreur affiché + aucune donnée n'a changé ✅

4. **Vérifier l'atomicité**:
   - Compter le nombre d'items avant l'import
   - Vérifier qu'après l'erreur, le nombre est identique
   - Si c'est le cas: ✅ PASS (ROLLBACK marche)
   - Si items 1 et 2 sont ajoutés: ❌ FAIL (pas de transaction)

---

## 7️⃣ TEST MANUEL: CORS

### Script JavaScript (console du navigateur)

```javascript
// Test 1: Requête depuis un domaine non-autorisé
try {
    fetch('http://localhost:8000/api/fridge', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
    }).then(r => r.json()).then(console.log);
} catch(e) {
    console.log("CORS bloquera ou acceptera selon config");
}

// ✅ ATTENDU (AFTER FIX):
// CORS error: Origin 'null' not in allow list

// ❌ AVANT (CURRENT):
// Requête acceptée (CORS * trop permissive)
```

---

## 8️⃣ TEST MANUEL: Validation Frontend

### Script JavaScript (console)

```javascript
// Ouvrir le scanner, essayer des codes-barre invalides
FrigoScan.Scanner.process(""); // Vide
FrigoScan.Scanner.process("a"); // Trop court
FrigoScan.Scanner.process("<img src=x>"); // Injection

// ✅ ATTENDU:
// Toast: "Code-barre invalide"

// ❌ CURRENT:
// Pas de message (envoyé directement à API)
```

---

## 🚀 INSTRUCTIONS D'EXÉCUTION

### Prérequis
```bash
# Installer les tests
pip install requests pytest

# Démarrer le serveur
cd c:\Users\natah\Desktop\FrigoScan
python -m uvicorn server.main:app --reload
# Le serveur tourne sur http://localhost:8000
```

### Lancer les tests
```bash
# Dans une autre terminal:
cd c:\Users\natah\Desktop\FrigoScan

# Test 1: Stack trace
python tests/test_error_exposure.py

# Test 2: Race conditions
python tests/test_concurrent_access.py

# Test 3: Validation inputs
python tests/test_input_validation.py

# Test 4: Pagination
python tests/test_pagination.py

# Test 5: Performance
python tests/test_performance.py
```

---

## 📊 RÉSUMÉ ATTENDU

Après exécution, vous devriez voir:

```
Test 1 - Stack trace:
  ❌ FAIL (avant fix)
  ✅ PASS (après fix)

Test 2 - Race conditions:
  ❌ FAIL: Plusieurs erreurs de DB (avant)
  ✅ PASS: 0 erreurs (après)

Test 3 - Validation:
  ❌ FAIL: 5+ tests failed (avant)
  ✅ PASS: 0 failed (après)

Test 4 - Pagination:
  ✅ Dépend de l'implémentation

Test 5 - Performance:
  ⚠️  WARNING: > 1s (avant)
  ✅ PASS: < 500ms (après indices)
```

---

## 💡 PROCHAINES ÉTAPES

1. Créer le répertoire `tests/`
2. Y mettre les scripts Python ci-dessus
3. Démarrer le serveur en dev
4. Exécuter les tests
5. Observer les failures
6. Implémenter les fixes de `RECOMMENDATIONS.md`
7. Re-exécuter les tests (vérifier PASS)

