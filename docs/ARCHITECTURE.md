# Architecture Technique — FriScan

## Vue d'ensemble

FriScan est une application web full-stack conçue pour être utilisée **sur une tablette Surface Pro en magasin**.
Le navigateur web sert d'interface tactile et accède à la webcam (avant/arrière), au flash et au micro.
Le serveur Python tourne en local et gère la logique métier et le stockage des données.

### Cas d'usage principal

```
┌──────────────────────────────────────────────┐
│           EN MAGASIN (Surface Pro)           │
│                                              │
│  1. Scanner le code-barres (webcam/douchette)│
│  2. Dicter la date (micro) ou calendrier     │
│  3. Produit ajouté automatiquement au frigo  │
│                                              │
│     → Tout se passe en local sur la tablette │
└──────────────────────────────────────────────┘
```

## Composants détaillés

### 1. Backend — FastAPI (Python)

**Pourquoi FastAPI ?**
- Rapide et moderne (asynchrone)
- Documentation API automatique (Swagger UI sur `/docs`)
- Validation des données via Pydantic
- Facile à apprendre pour un débutant

**Structure :**
```
server/
├── app.py            → Point d'entrée, configure FastAPI et les routes
├── database.py       → Connexion SQLite avec SQLAlchemy ORM
├── models.py         → Modèles de données (tables DB + schémas API)
├── routers/
│   ├── products.py   → CRUD produits (ajouter/lister/modifier/supprimer)
│   ├── scanner.py    → Scan barcode (image ou texte) + recherche Open Food Facts
│   ├── recipes.py    → Suggestions de recettes
│   └── fresh_products.py → Produits frais sans code-barres
└── services/
    ├── openfoodfacts.py → Client HTTP pour l'API Open Food Facts
    ├── barcode.py       → Décodage de codes-barres (pyzbar)
    └── recipe_engine.py → Algorithme de suggestion de recettes
```

### 2. Base de données — SQLite

- Stockée dans `server/data/friscan.db`
- Créée automatiquement au premier lancement
- Un seul fichier, pas d'installation serveur DB
- Table `products` avec tous les champs nécessaires

### 3. Scanner de codes-barres

**Option A : Webcam (via navigateur)**
- La webcam est accédée via `navigator.mediaDevices.getUserMedia()`
- **Multi-caméra** : énumération des caméras via `enumerateDevices()`, bascule avant/arrière
- **Flash / Torche** : activation via `MediaStreamTrack.applyConstraints({ advanced: [{ torch: true }] })`
- L'image est capturée sur un canvas HTML5
- Envoyée au serveur qui décode avec `pyzbar`
- Scan automatique toutes les 1.5 secondes

**Option B : Douchette USB**
- La douchette s'émule comme un clavier
- Elle "tape" le code-barres + touche Entrée
- Le JavaScript détecte la saisie rapide et lance la recherche

**Option C : Saisie manuelle**
- Champ texte simple pour taper le code

### 4. Open Food Facts

- API REST publique et gratuite
- URL : `https://world.openfoodfacts.org/api/v2/product/{barcode}.json`
- Retourne : nom, marque, catégorie, image, Nutri-Score, quantité
- Aucune clé API nécessaire
- Fonctionne pour les produits vendus en France et dans le monde

### 5. Reconnaissance vocale

- Utilise la **Web Speech API** native du navigateur
- Pas d'installation supplémentaire
- Fonctionne dans Chrome, Edge, Safari
- Le texte dicté est parsé en français pour extraire une date
- Formats supportés : "quinze mars 2026", "15/03/2026", "le 3 avril"

**Considérations pour l'environnement bruyant (supermarché) :**
- Le micro intégré de la Surface Pro est utilisé
- La Web Speech API intègre un filtrage de bruit basique
- En cas d'échec de reconnaissance, le calendrier tactile prend le relais
- Interface visuelle de feedback pour indiquer l'état de l'écoute

### 6. Calendrier tactile

- Sélecteur de date grand format, optimisé pour les doigts
- Boutons mois/année larges (minimum 48px de zone tactile)
- Jours affichés en grille avec taille suffisante pour la sélection au doigt
- Alternative fiable à la saisie vocale dans un environnement bruyant

### 7. Moteur de recettes

- Base locale de 20+ recettes françaises (extensible via JSON)
- Algorithme de correspondance :
  1. Compare chaque ingrédient de recette avec les produits du frigo
  2. Utilise une correspondance floue (SequenceMatcher, seuil 60%)
  3. Calcule un score = ingrédients trouvés / total ingrédients
  4. Bonus pour les produits proches de la péremption
  5. Trie par pertinence décroissante

### 8. Interface tactile (Surface Pro)

**Principes de design :**
- **Touch-first** : tous les éléments interactifs ont une zone de touche ≥ 48×48px
- **Boutons larges** : texte lisible, espacement généreux
- **Navigation par onglets** : accès rapide aux 4 sections principales
- **Responsive** : s'adapte du mode tablette (portrait) au mode laptop (paysage)
- **Feedback visuel** : animations et couleurs pour confirmer les actions

## Flux de données

```
Utilisateur  →  Surface Pro (webcam/micro)  →  Serveur FastAPI (local)  →  SQLite
                                                       ↕
                                                Open Food Facts API
```

### Scan d'un produit :
1. L'utilisateur scanne un code-barres (webcam/douchette/manuel)
2. Le serveur décode le code-barres
3. Le serveur interroge Open Food Facts
4. Les infos du produit s'affichent
5. L'utilisateur dicte ou sélectionne la date de péremption (voix ou calendrier tactile)
6. Le produit est enregistré en base

### Suggestion de recettes :
1. Le serveur récupère tous les produits du frigo
2. Le moteur compare avec la base de recettes
3. Les recettes sont triées par pertinence
4. Les produits bientôt périmés sont favorisés

## Plateforme cible

| Caractéristique | Détail |
|-----------------|--------|
| **Appareil** | Microsoft Surface Pro (ou tablette Windows) |
| **OS** | Windows 10/11 |
| **Navigateur** | Microsoft Edge (recommandé) ou Chrome |
| **Entrées** | Écran tactile, douchette USB, webcam, micro intégré |
| **Réseau** | Wi-Fi du magasin ou partage de connexion mobile |
| **Serveur** | Local (localhost:8000), pas de cloud nécessaire |
