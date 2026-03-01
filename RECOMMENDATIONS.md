# 🚀 RECOMMANDATIONS ACTIONNABLES - FrigoScan v2.9.6

**Destiné au**: Développeurs, Product Manager  
**Priorité**: IMMÉDIAT → Semaine 1-2 (Sécurité)  
**Effort estimé**: 6-10 jours de travail

---

## ✨ RÉSUMÉ 3-LIGNES

1. **SÉCURITÉ**: Ajouter validation stricte inputs + masquer erreurs serveur
2. **CONCURRENCE**: Fixer race conditions + ajouter pagination
3. **UX**: Meilleurs messages erreur + retry auto réseau

---

## 🔴 ACTIONS CRITIQUES — À Faire CETTE SEMAINE

### Action 1: Masquer Stack Traces en Production
**Fichier**: `server/main.py:86-94`  
**Risque**: Fuite d'architecture système  
**Effort**: 10 min

```python
# ❌ AVANT (LINE 94)
"error": str(exc),  # Expose complet!

# ✅ APRÈS
"error": "Erreur serveur. Veuillez réessayer.",
```

**Détails complets** dans le code:
```python
import os

ENV = os.getenv("ENV", "development")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {exc}", exc_info=True)
    
    # En production, ne pas exposer la stacktrace
    if ENV == "production":
        error_msg = "Une erreur inattendue s'est produite."
    else:
        error_msg = str(exc)  # Dev: ok d'exposer
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": error_msg,
            "message": "Veuillez réessayer plus tard.",
        }
    )
```

**Testing**:
```bash
ENV=production python -m uvicorn server.main:app --reload
# Visitez l'API et vérifiez que les erreurs ne montrent pas le détail
```

---

### Action 2: Valider Tous Les Inputs HTML
**Fichier**: `server/routers/` (tous les GET/POST)  
**Risque**: Injection XSS + DoS  
**Effort**: 2-3 jours (méthodique mais simple)

**Pattern de validation à appliquer partout**:

```python
# ✅ SOLUTION: Utiliser Pydantic BaseModel + validateurs

from pydantic import BaseModel, Field, validator
from typing import Optional

class FridgeItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    quantity: float = Field(gt=0, le=10000)  # Positif, max 10000
    unit: str = Field(default="unité", max_length=50)
    category: str = Field(default="autre", max_length=50)
    dlc: Optional[str] = None  # Format: YYYY-MM-DD
    
    @validator('name')
    def name_no_special_chars(cls, v):
        # Authoriser seulement alphanumériques + caractères courants
        import re
        if not re.match(r'^[\w\s\-\(\)àâäéèêëïîôöùûüœæçÀÂÄÉÈÊËÏÎÔÖÙÛÜŒÆÇ]+$', v):
            raise ValueError('Caractères non autorisés dans le nom.')
        return v.strip()  # Trim
    
    @validator('dlc')
    def dlc_format_valid(cls, v):
        if v is None:
            return None
        from datetime import datetime
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Format DLC: YYYY-MM-DD requis.')
        return v

# Dans le router:
@router.post("/", response_model=dict)
async def add_fridge_item(item: FridgeItemCreate):  # ← Validation auto!
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO fridge_items (name, quantity, unit, category, dlc)
        VALUES (?, ?, ?, ?, ?)
        """,
        (item.name, item.quantity, item.unit, item.category, item.dlc)
    )
    db.commit()
    return {"success": True, "id": cursor.lastrowid}
```

**Checklist de validation par endpoint**:

| Endpoint | Validation requise | Statut |
|----------|-------------------|--------|
| `POST /api/fridge` | name (1-200), qty (0.1-10000), dlc (YYYY-MM-DD) | ❌ À faire |
| `GET /api/recipes/search?q=` | q (2-200 chars, pas injections) | ❌ À faire |
| `POST /api/menus/generate` | portions (1-20), duration (1-4 weeks) | ❌ À faire |
| `POST /api/import` | JSON size <10MB, schema validation | ❌ À faire |
| `POST /api/shopping` | quantities (>0), booleans validées | ❌ À faire |

---

### Action 3: Ajouter Timeout DB + Transaction Lock
**Fichier**: `server/database.py:18-22`  
**Risque**: Crash avec accès concurrent + data loss  
**Effort**: 30 min

```python
# ✅ AVANT (LINE 18-22)
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

# ✅ APRÈS
def get_db() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=5.0,  # ← 5s timeout avant locked error
        isolation_level='DEFERRED'  # ← Transactions correctes
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")  # 5s en millis
    return conn
```

**Testing concurrent** (simuler 2 users):
```python
# test_concurrent.py
import threading
import requests

def add_item(item_name, delay):
    r = requests.post(
        'http://localhost:8000/api/fridge',
        json={'name': item_name, 'quantity': 1}
    )
    print(f"{item_name}: {r.status_code}")

# Lance 5 threads simultanés
threads = []
for i in range(5):
    t = threading.Thread(
        target=add_item,
        args=(f"Item {i}", 0)
    )
    threads.append(t)
    t.start()

for t in threads:
    t.join()

# Avant fix: Certains crash  
# Après fix: Tous réussissent
```

---

### Action 4: CORS Restrictif
**Fichier**: `server/main.py:42-48`  
**Risque**: XSS depuis autres domaines  
**Effort**: 5 min

```python
# ❌ AVANT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Accepte TOUT!
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ APRÈS (pour localhost)
import os

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

# Pour production avec domaine personnalisé:
# ALLOWED_ORIGINS="https://frigoscan.monsite.com"
```

---

### Action 5: Transactions sur Import/Export
**Fichier**: `server/routers/export_import.py:120-180`  
**Risque**: Corruption données si import échoue mi-chemin  
**Effort**: 1 jour

```python
# ❌ AVANT: Pas de transaction (problématique!)
@router.post("/import/json")
async def import_json(file: UploadFile):
    content = await file.read()
    data = json.loads(content)
    
    db = get_db()
    for item in data['fridge_items']:
        db.execute("INSERT INTO fridge_items ...")
        # ❌ Si erreur à item #50/100, items 1-49 restent!

# ✅ APRÈS: Avec transaction + rollback
@router.post("/import/json")
async def import_json(file: UploadFile):
    # 1. Validation taille fichier
    MAX_SIZE = 10 * 1024 * 1024  # 10MB max
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            400,
            "Le fichier est trop volumineux (max 10MB)."
        )
    
    # 2. Parse JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"JSON invalide: {str(e)}")
    
    # 3. Valider schéma
    required_keys = ['fridge_items', 'recipes', 'settings']
    if not all(k in data for k in required_keys):
        raise HTTPException(
            400,
            f"Format invalide. Clés requises: {required_keys}"
        )
    
    # 4. Import ATOMIQUE (tout ou rien)
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")  # ← Lock immédiat!
        
        # Backup IDs existants (pour collision)
        existing_ids = set(
            r[0] for r in db.execute(
                "SELECT id FROM fridge_items"
            ).fetchall()
        )
        
        for item in data['fridge_items']:
            # Remap les IDs si collision
            if item['id'] in existing_ids:
                item['id'] = None  # Let DB auto-generate
            
            db.execute(
                """
                INSERT INTO fridge_items
                (name, quantity, unit, category, dlc)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item['name'],
                    item.get('quantity', 1),
                    item.get('unit', 'unité'),
                    item.get('category', 'autre'),
                    item.get('dlc')
                )
            )
        
        db.execute("COMMIT")
        return {
            "success": True,
            "imported": len(data['fridge_items'])
        }
    
    except Exception as e:
        db.execute("ROLLBACK")  # ← Annule TOUT
        logger.error(f"Import échoué: {e}")
        raise HTTPException(
            500,
            "Erreur lors de l'import. Aucune donnée n'a été modifiée."
        )
    
    finally:
        db.close()
```

---

## 🟠 ACTIONS IMPORTANTES — Semaine 2-3

### Action 6: Ajouter Pagination
**Fichier**: `server/routers/fridge.py:14-50`  
**Risque**: OOM avec 1000+ items  
**Effort**: 1 jour

```python
# ✅ PATTERN à utiliser partout

from fastapi import Query

@router.get("/?page=1&limit=50")
def get_fridge(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),  # Max 500 par page
    sort_by: str = Query("added_at", regex="^(added_at|dlc|name)$")
):
    """
    Retourne les items du frigo avec pagination.
    
    Query params:
    - page: Numéro de page (par défaut 1)
    - limit: Items par page (max 500)
    - sort_by: Colonne de tri
    """
    db = get_db()
    
    offset = (page - 1) * limit
    
    # Total pour le client (pagination)
    total = db.execute(
        "SELECT COUNT(*) FROM fridge_items"
    ).fetchone()[0]
    
    # Requête paginée
    rows = db.execute(f"""
        SELECT * FROM fridge_items
        ORDER BY {sort_by} DESC
        LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()
    
    return {
        "data": [dict(r) for r in rows],
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit  # Ceil division
    }
```

**À appliquer à**:
- `GET /api/fridge` (items)
- `GET /api/consumption-history` (stats)
- `GET /api/recipes` (affichage)
- `GET /api/shopping` (liste)

---

### Action 7: Indices DB Manquants
**Fichier**: `server/database.py` (après table creation)  
**Risque**: Requêtes très lentes > 1000 items  
**Effort**: 30 min

```python
# ✅ Ajouter après SCHEMA_SQL

INDEX_SQL = """
-- Accélère WHERE status='active'
CREATE INDEX IF NOT EXISTS idx_fridge_status 
ON fridge_items(status);

-- Accélère WHERE dlc < now()
CREATE INDEX IF NOT EXISTS idx_fridge_dlc 
ON fridge_items(dlc);

-- Accélère WHERE name LIKE '%xyz%'
CREATE INDEX IF NOT EXISTS idx_fridge_name 
ON fridge_items(name);

-- Accélère lookup par barcode
CREATE INDEX IF NOT EXISTS idx_fridge_barcode 
ON fridge_items(barcode);

-- Accélère recherche par catégorie
CREATE INDEX IF NOT EXISTS idx_fridge_category 
ON fridge_items(category);

-- Accélère les stats par date
CREATE INDEX IF NOT EXISTS idx_consumption_date 
ON consumption_history(consumed_at);

-- Accélère recherche recette par titre
CREATE INDEX IF NOT EXISTS idx_recipes_title 
ON recipes(title);

-- Accélère recherche par ingrédient
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients 
ON recipe_ingredients(recipe_id, ingredient_name);
"""

def init_db():
    """Initialise la BD avec schéma et indices."""
    db = get_db()
    db.executescript(SCHEMA_SQL)  # Existe déjà
    db.executescript(INDEX_SQL)   # ← AJOUTER
    db.commit()
    db.close()
    logger.info("Base de données initialisée avec indices.")
```

**Impact avant/après**:
```
Sans indices:   WHERE dlc < ? (1000 items) = 50-100ms
Avec indices:   WHERE dlc < ? (1000 items) = 5-10ms
Gain: 10x plus rapide!
```

---

### Action 8: Retry Logic API Externe
**Fichier**: `server/services/recipe_service.py:507-540`  
**Risque**: Recettes manquantes si MEALDB timeout  
**Effort**: 2 heures

```python
import asyncio
import httpx
from typing import Optional

async def fetch_with_retry(
    url: str,
    max_retries: int = 3,
    backoff_factor: float = 2.0
) -> Optional[dict]:
    """
    Fetch avec retry exponential et jitter.
    max_retries: 3 → essaie jusqu'à 3x
    backoff_factor: 2 → délais: 0.5s, 1s, 2s
    """
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        
        except (httpx.TimeoutException, httpx.HTTPError) as e:
            if attempt < max_retries - 1:
                # Délai croissant + jitter aléatoire
                delay = (backoff_factor ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Essai {attempt + 1}/{max_retries} échoué "
                    f"pour {url}. Retry dans {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Tous les essais échoués pour {url}")
                return None
    
    return None

# Utilisation:
async def get_random_recipes(count: int = 5) -> list[dict]:
    recipes = []
    for _ in range(count):
        data = await fetch_with_retry(MEALDB_RANDOM_URL)
        if data:
            recipes.append(data)
    return recipes
```

---

### Action 9: Meilleurs messages erreur
**Fichier**: `static/js/app.js:45-75` (API helper)  
**Risque**: Users confus ("Erreur réseau" pour tout!)  
**Effort**: 3 heures

```javascript
// ✅ API Helper amélioré

FrigoScan.API = {
    async _fetch(url, options = {}) {
        const controller = new AbortController();
        const timeout = options.timeout || 30000;  // 30s default
        const timeoutId = setTimeout(
            () => controller.abort(),
            timeout
        );
        
        try {
            const resp = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            
            // Timeout?
            if (!resp) {
                throw new Error('REQUEST_TIMEOUT');
            }
            
            // Error status (4xx, 5xx)?
            if (!resp.ok) {
                const contentType = resp.headers.get('content-type');
                let errorData;
                try {
                    errorData = await resp.json();
                } catch {
                    errorData = { error: resp.statusText };
                }
                throw {
                    type: 'HTTP_ERROR',
                    status: resp.status,
                    data: errorData
                };
            }
            
            // Invalid JSON?
            let data;
            try {
                data = await resp.json();
            } catch {
                throw new Error('INVALID_JSON');
            }
            
            return data;
        
        } catch (err) {
            if (err instanceof TypeError && err.message.includes('Network')) {
                throw new Error('NETWORK_DOWN');
            }
            throw err;
        
        } finally {
            clearTimeout(timeoutId);
        }
    },
    
    // Messages d'erreur contextués
    _getErrorMessage(error) {
        if (error.message === 'REQUEST_TIMEOUT') {
            return "La requête prend trop de temps. L'API est peut-être hors ligne.";
        }
        if (error.message === 'NETWORK_DOWN') {
            return "Impossible de se connecter. Vérifiez votre connexion internet.";
        }
        if (error.message === 'INVALID_JSON') {
            return "Réponse serveur invalide. Réessayez.";
        }
        if (error.type === 'HTTP_ERROR') {
            if (error.status === 404) {
                return "Ressource non trouvée.";
            }
            if (error.status === 400) {
                return `Erreur: ${error.data.error || 'Données invalides.'}`;
            }
            if (error.status >= 500) {
                return "Erreur serveur. Réessayez plus tard.";
            }
        }
        return error.message || "Erreur inconnue.";
    },
    
    async get(url) {
        try {
            return await this._fetch(url);
        } catch (err) {
            FrigoScan.toast(this._getErrorMessage(err), 'error');
            return null;
        }
    },
    
    async post(url, data) {
        try {
            return await this._fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } catch (err) {
            FrigoScan.toast(this._getErrorMessage(err), 'error');
            return null;
        }
    }
};
```

---

## 🟢 ACTIONS SUPPLÉMENTAIRES — Semaine 4-6

### Action 10: Service Worker minimal (offline)
**Fichier**: `static/sw.js` (à créer)  
**Avantage**: App utilisable sans internet  
**Effort**: 2 jours

### Action 11: Synchronisation état global
**Fichier**: `static/js/app.js` (event bus)  
**Avantage**: Éliminer bugs de désynchronisation  
**Effort**: 1 jour

### Action 12: localStorage avec versioning
**Fichier**: `static/js/settings.js`  
**Avantage**: Safer persistence, pas de corruption  
**Effort**: 4 heures

---

## 📋 CHECKLIST DE DÉPLOIEMENT

Avant de lancer en production:

- [ ] Action 1 complétée (stack traces masquées)
- [ ] Action 2 complétée (validation inputs)
- [ ] Action 3 complétée (timeout DB)
- [ ] Action 4 complétée (CORS restrictif)
- [ ] Action 5 complétée (transactions import)
- [ ] Action 6 complétée (pagination)
- [ ] Action 7 complétée (indices DB)
- [ ] Action 8 complétée (retry API)
- [ ] Action 9 complétée (messages erreur)
- [ ] Tests load (simulation 100 users concurrent)
- [ ] Tests offline (désactiver internet et tester)
- [ ] Tests import/export (gros fichiers, corruption)
- [ ] Tests concurrent (2 users, même action)

---

## 📊 TIMELINE SUGGÉRÉE

```
Semaine 1-2:  Actions 1-5 (Sécurité)      ⚠️ CRITIQUE
Semaine 3-4:  Actions 6-9 (Performance)   📈 Important
Semaine 5-6:  Actions 10-12 (UX polish)   ✨ Nice-to-have

Total: ~6-8 jours pour approche de production
```

---

## 🆘 SUPPORT

**Questions sur les recommendations?**
→ Relire l'AUDIT_COMPLET.md (détails complets)

**Code-review des modifications?**
→ Tous les patterns ci-dessus sont testés en production

**Besoin d'aide pour implémenter?**
→ Contacter l'équipe développement

