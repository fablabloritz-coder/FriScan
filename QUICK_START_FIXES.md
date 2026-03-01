# ⚡ QUICK START — Implémenter les Corrections Critiques

**Pour**: Développeurs impatients de fixer les problèmes immédiatement  
**Durée**: ~4 heures pour implémenter Actions 1-5  
**Complexité**: Faible à Moyen

---

## 🔥 AVANT DE COMMENCER

1. **Créer une branche git**:
   ```bash
   git checkout -b hotfix/security-audit
   ```

2. **Faire un backup de la BD**:
   ```bash
   cp server/data/frigoscan.db server/data/frigoscan.db.backup
   ```

3. **Arrêter le serveur**:
   ```bash
   # Si uvicorn tourne, Ctrl+C
   ```

---

## ✅ ACTION 1: Masquer Stack Traces (10 min)

**Fichier**: `server/main.py`

```python
# AVANT (lignes 86-94)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),  # ❌ Expose tout!
            "message": "Une erreur inattendue s'est produite.",
        }
    )

# APRÈS
import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {exc}", exc_info=True)
    
    # En production, ne pas exposer la stacktrace
    error_msg = str(exc) if DEBUG else "Erreur serveur"
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": error_msg,
            "message": "Une erreur inattendue s'est produite.",
        }
    )
```

**Test**:
```bash
# Dev (debug mode)
DEBUG=true python -m uvicorn server.main:app --reload
# Vérifier: les erreurs montrent les détails

# Prod (no debug)
DEBUG=false python -m uvicorn server.main:app --reload
# Vérifier: les erreurs sont vagues
```

✅ **DONE!**

---

## ✅ ACTION 2: Timeout DB (15 min)

**Fichier**: `server/database.py`

```python
# AVANT (lignes 16-22)
def get_db() -> sqlite3.Connection:
    """Retourne une connexion SQLite avec row_factory = Row."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))  # ❌ Pas de timeout!
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

# APRÈS
def get_db() -> sqlite3.Connection:
    """Retourne une connexion SQLite avec row_factory = Row."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    # ✅ Ajouter timeout=5.0 (5 secondes)
    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=5.0,  # ← CRITICAL: Évite les crashes si DB locked
        isolation_level='DEFERRED'  # ← Transactions plus intelligentes
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")  # 5s en millis aussi
    return conn
```

**Test concurrent**:
```bash
# Lancer 2 scripts Python en même temps qui font des writes
# AVANT: Crash possible
# APRÈS: Tous les deux réussissent
```

✅ **DONE!**

---

## ✅ ACTION 3: CORS Restrictif (5 min)

**Fichier**: `server/main.py` (aussi au top du fichier)

```python
# AVANT (lignes 42-48)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ Accepte TOUT!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APRÈS
import os

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # ← Explicite
    allow_headers=["Content-Type"],  # ← Minimal
)
```

**Test**:
```bash
# Dev local (default)
python -m uvicorn server.main:app --reload
# Vérifier: Fonctionne toujours sur localhost:8000

# Prod avec domaine perso
ALLOWED_ORIGINS="https://frigoscan.monsite.com" \
  python -m uvicorn server.main:app
# Vérifier: Seulement depuis ce domaine
```

✅ **DONE!**

---

## ✅ ACTION 4: Validation Input - Template (1 jour)

**Le pattern à utiliser partout dans les routers**:

### Example: `server/routers/fridge.py`

**AVANT**:
```python
@router.post("/")
async def add_fridge_item(
    name: str,
    quantity: float = 1,
    unit: str = "unité",
    category: str = "autre",
    dlc: Optional[str] = None
):
    # ❌ Pas de validation!
    db = get_db()
    db.execute(
        "INSERT INTO fridge_items (name, quantity, unit, category, dlc) VALUES (?, ?, ?, ?, ?)",
        (name, quantity, unit, category, dlc)
    )
    db.commit()
    return {"success": True}
```

**APRÈS**:
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
import re
from datetime import datetime

# 1. Définir le modèle de validation
class FridgeItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    quantity: float = Field(gt=0, le=10000)
    unit: str = Field(default="unité", max_length=50)
    category: str = Field(default="autre", max_length=50)
    dlc: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        # Trim et vérifier les caractères
        v = v.strip()
        
        # Pattern: alphabets, chiffres, tirets, parenthèses, accents
        if not re.match(
            r'^[\w\s\-\(\)àâäéèêëïîôöùûüœæçÀÂÄÉÈÊËÏÎÔÖÙÛÜŒÆÇ\.\,]+$',
            v
        ):
            raise ValueError(
                'Caractères non autorisés. Utilisez lettres, chiffres, -, ()'
            )
        
        if len(v) == 0:
            raise ValueError('Le nom ne peut pas être vide.')
        
        return v
    
    @validator('dlc')
    def validate_dlc(cls, v):
        if v is None:
            return None
        
        try:
            # Vérifier format YYYY-MM-DD
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Format DLC: YYYY-MM-DD requis (ex: 2025-12-31)')
        
        return v
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantité doit être positive.')
        if v > 10000:
            raise ValueError('Quantité max: 10000.')
        return v

# 2. Utiliser le modèle dans les routes
@router.post("/")
async def add_fridge_item(item: FridgeItemCreate):  # ← Validation auto!
    """Ajouter un item au frigo."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        """
        INSERT INTO fridge_items 
        (name, quantity, unit, category, dlc, status)
        VALUES (?, ?, ?, ?, ?, 'active')
        """,
        (item.name, item.quantity, item.unit, item.category, item.dlc)
    )
    db.commit()
    
    return {
        "success": True,
        "id": cursor.lastrowid,
        "item": {
            "id": cursor.lastrowid,
            "name": item.name,
            "quantity": item.quantity,
            "unit": item.unit,
        }
    }
```

**À appliquer à TOUS les POST/PUT endpoints**:
- `POST /api/fridge` ← Faire en priorité
- `POST /api/menus/generate`
- `POST /api/shopping`
- `POST /api/import`
- Etc.

**Test**:
```bash
# Test valide
curl -X POST http://localhost:8000/api/fridge \
  -H "Content-Type: application/json" \
  -d '{"name": "Lait", "quantity": 1d}'
# ✅ 200: Accepté

# Test invalide: nom vide
curl -X POST http://localhost:8000/api/fridge \
  -H "Content-Type: application/json" \
  -d '{"name": "", "quantity": 1}'
# ❌ 422: Rejeté (validation error)

# Test invalide: quantité négative
curl -X POST http://localhost:8000/api/fridge \
  -H "Content-Type: application/json" \
  -d '{"name": "Lait", "quantity": -5}'
# ❌ 422: Rejeté
```

✅ **DONE!**

---

## ✅ ACTION 5: Transactions sur Import (2 heures)

**Fichier**: `server/routers/export_import.py` (lignes 120-180)

**Avant**: Pas de transaction

**Après**:
```python
@router.post("/import/json")
async def import_json(file: UploadFile):
    """Importer frigo depuis JSON."""
    
    # 1. Validation taille fichier
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    
    if len(content) > MAX_SIZE:
        raise HTTPException(
            400,
            f"Fichier trop volumineux ({len(content)} > {MAX_SIZE} bytes)"
        )
    
    # 2. Parse JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(
            400,
            f"JSON invalide: {str(e)}"
        )
    
    # 3. Valider schéma (clés obligatoires)
    required_keys = {'fridge_items', 'settings'}
    missing_keys = required_keys - set(data.keys())
    if missing_keys:
        raise HTTPException(
            400,
            f"Clés manquantes: {', '.join(missing_keys)}"
        )
    
    # 4. Import ATOMIQUE (everything or nothing)
    db = get_db()
    try:
        # Démarrer transaction IMMEDIATEMENT
        db.execute("BEGIN IMMEDIATE")
        
        # Clear les anciennes données
        db.execute("DELETE FROM fridge_items")
        
        # Insérer les nouvelles
        for idx, item in enumerate(data.get('fridge_items', [])):
            try:
                db.execute(
                    """
                    INSERT INTO fridge_items
                    (name, quantity, unit, category, dlc, status)
                    VALUES (?, ?, ?, ?, ?, 'active')
                    """,
                    (
                        item.get('name'),
                        item.get('quantity', 1),
                        item.get('unit', 'unité'),
                        item.get('category', 'autre'),
                        item.get('dlc'),
                    )
                )
            except Exception as e:
                raise ValueError(
                    f"Item #{idx} invalide: {str(e)}"
                )
        
        # COMMIT si tout réussit
        db.commit()
        logger.info(f"Import réussi: {len(data['fridge_items'])} items")
        
        return {
            "success": True,
            "imported": len(data['fridge_items']),
            "message": f"{len(data['fridge_items'])} articles importés."
        }
    
    except Exception as e:
        # ROLLBACK si erreur!
        db.rollback()
        logger.error(f"Import échoué, ROLLBACK: {e}")
        
        raise HTTPException(
            500,
            f"Erreur import: {str(e)}. Aucune donnée n'a été modifiée."
        )
    
    finally:
        db.close()
```

**Test**:
```bash
# Créer un fichier invalide (mais bien formé)
cat > bad.json << 'EOF'
{
  "fridge_items": [
    {"name": "Bon item", "quantity": 1},
    {"name": "Mauvais item", "quantity": "NOT A NUMBER"},
    {"name": "Item 3", "quantity": 1}
  ],
  "settings": {}
}
EOF

# Compter les items avant
curl http://localhost:8000/api/fridge | jq '.data | length'
# Résultat: 5 (par exemple)

# Essayer l'import
curl -F "file=@bad.json" http://localhost:8000/api/import/json
# Résultat: 500 error + message

# Vérifier que RIEN n'a changé!
curl http://localhost:8000/api/fridge | jq '.data | length'
# Résultat: 5 (identique! ROLLBACK marche)
```

✅ **DONE!**

---

## 🧪 VÉRIFIER TOUT FONCTIONNE

Après avoir implémenté les 5 actions:

```bash
# Redémarrer le serveur
cd c:\Users\natah\Desktop\FrigoScan
DEBUG=false python -m uvicorn server.main:app --reload

# Dans une autre terminal, lancer les tests
python tests/test_error_exposure.py
python tests/test_concurrent_access.py
python tests/test_input_validation.py

# Vérifier les résultats
```

**Si vous voyez**:
```
✅ Test 1 - Stack trace: PASS
✅ Test 2 - Concurrent: PASS (0 errors)
✅ Test 3 - Validation: PASS (tous les inputs rejetés)
```

→ **Vous avez réussi!** 🎉

---

## 📋 COMMIT & PUSH

```bash
git add -A
git commit -m "Hotfix: Sécurité critique (masquer erreurs, validation, concurrence, CORS, transactions)"
git push origin hotfix/security-audit

# Créer une PR pour review
```

---

## ⏱️ TEMPS RÉEL

| Action | Temps | Difficulté |
|--------|-------|-----------|
| 1. Stack traces | 10 min | ★☆☆ Trivial |
| 2. Timeout DB | 15 min | ★☆☆ Trivial |
| 3. CORS | 5 min | ★☆☆ Trivial |
| 4. Validation Input | 2-3h | ★★☆ Moyen |
| 5. Transactions | 1-2h | ★★☆ Moyen |
| **Tests complets** | 30 min | ★☆☆ Trivial |
| **Total** | ~4-5h | ★★☆ Moyen |

---

## 🚀 PROCHAINES ÉTAPES

Une fois ces 5 actions complétées et testées:

1. ✅ Refaire les tests (doivent tous PASS)
2. ✅ Livrer v2.9.7 (security update)
3. ➡️ Continuer avec Action 6-9 (performance + robustesse)
4. ➡️ Puis Actions 10-12 (UX + polish)

---

## 💡 TIPS

- Garder les changements **petits et testables**
- Revert immédiatement si un test échoue
- Commiter après chaque action
- Tester en `DEBUG=true` et `DEBUG=false`

**Happy coding! 🚀**

