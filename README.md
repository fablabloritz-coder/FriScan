# 🧊 FriScan — Gestionnaire Intelligent de Frigo

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/FastAPI-0.104%2B-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Licence-MIT-green?logo=opensourceinitiative&logoColor=white" alt="MIT License">
  <img src="https://img.shields.io/badge/Platform-Surface%20Pro-0078D4?logo=windows&logoColor=white" alt="Surface Pro">
</p>

<p align="center">
  <a href="#-fonctionnalités"><strong>Fonctionnalités</strong></a> ·
  <a href="#-installation"><strong>Installation</strong></a> ·
  <a href="#-utilisation"><strong>Utilisation</strong></a> ·
  <a href="#-contribuer"><strong>Contribuer</strong></a> ·
  <a href="#-licence"><strong>Licence</strong></a>
</p>

---

## 📖 Présentation

**FriScan** est un système autonome open-source conçu pour être **emmené en courses sur une tablette Surface Pro**. Il permet de :

- **Scanner les produits** en magasin (douchette USB ou webcam intégrée)
- **Suivre les dates limites de consommation** (saisie vocale ou calendrier tactile)
- **Gérer le contenu du frigo** à distance
- **Recevoir des suggestions de recettes** adaptées aux produits disponibles

### 🎯 Concept

L'idée est simple : vous emportez votre Surface Pro au supermarché. Chaque produit ajouté au chariot est scanné en temps réel. La date de péremption est dictée au micro ou sélectionnée sur un calendrier tactile. En rentrant, votre frigo virtuel est déjà à jour.

| Scénario | Comment ça marche |
|----------|-------------------|
| **En magasin** | Scanner les codes-barres → dicter/sélectionner la date → produit ajouté |
| **À la maison** | Consulter le frigo, voir les produits bientôt périmés, obtenir des idées recettes |
| **Au quotidien** | Alertes de péremption, suggestions de recettes pour éviter le gaspillage |

---

## ✨ Fonctionnalités

### Scanner de codes-barres
- 📷 **Webcam** : scan via la caméra intégrée de la Surface Pro
- 🔄 **Changement de caméra** : bascule entre la webcam avant et arrière
- 💡 **Flash / Torche** : activation du flash pour scanner en faible luminosité
- 🔫 **Douchette USB** : support des scanners USB (émulation clavier)
- ⌨️ **Saisie manuelle** : champ texte pour entrer le code-barres à la main

### Saisie de la date de péremption
- 🎤 **Reconnaissance vocale** : dictez la date en français ("quinze mars 2026")
- 📅 **Calendrier tactile** : sélecteur grand format optimisé pour l'écran tactile
- 🔊 **Environnement bruyant** : conçu pour fonctionner avec le micro intégré de la tablette

### Gestion du frigo
- 📦 **Ajout automatique** via Open Food Facts (nom, marque, catégorie, Nutri-Score, image)
- 🥕 **Produits frais** : ajout manuel pour fruits, légumes, viande à la coupe, etc.
- ⚠️ **Alertes péremption** : notifications pour les produits proches de la date limite
- 🔍 **Recherche et filtres** : retrouvez vos produits rapidement

### Recettes intelligentes
- 🍳 **Suggestions adaptées** : recettes basées sur le contenu réel de votre frigo
- ♻️ **Anti-gaspillage** : priorisation des produits bientôt périmés
- 📚 **Base extensible** : 20+ recettes françaises, extensible via JSON

### Interface tactile
- 📱 **Optimisée Surface Pro** : boutons larges, zones de touche généreuses
- 🖐️ **Touch-first** : conçue pour l'interaction au doigt
- 📏 **Responsive** : s'adapte à toutes les tailles d'écran

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              SURFACE PRO (Tablette en magasin)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Scanner  │  │  Saisie  │  │  Liste   │  │  Recettes  │  │
│  │ barcode  │  │ vocale   │  │  frigo   │  │  suggérées │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │             │               │         │
└───────┼──────────────┼─────────────┼───────────────┼─────────┘
        │              │             │               │
        ▼              ▼             ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                   SERVEUR BACKEND (FastAPI)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ API      │  │ Open     │  │ Gestion  │  │ Moteur     │  │
│  │ Scanner  │  │ Food     │  │ Produits │  │ Recettes   │  │
│  │          │  │ Facts    │  │          │  │            │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│                         │                                    │
│                    ┌────┴────┐                               │
│                    │ SQLite  │                               │
│                    │   DB    │                               │
│                    └─────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

> 📄 Documentation technique détaillée : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 🛠️ Technologies

| Composant | Technologie | Rôle |
|-----------|------------|------|
| Backend | Python + FastAPI | API REST, logique métier |
| Base de données | SQLite | Stockage produits, recettes |
| Scanner barcode | OpenCV + pyzbar | Décodage codes-barres |
| Webcam | MediaDevices API | Accès caméras, switch, flash |
| Reconnaissance vocale | Web Speech API | Saisie vocale des dates |
| Données produits | Open Food Facts API | Infos nutritionnelles |
| Frontend | HTML/CSS/JS (vanilla) | Interface tactile |
| Recettes | Base locale JSON + algorithme | Suggestions adaptées |

---

## 📋 Prérequis

- **Python 3.10+** ([télécharger](https://www.python.org/downloads/))
- **Windows 10/11** (Surface Pro ou PC)
- **Navigateur moderne** : Edge, Chrome ou Firefox
- **Webcam** et/ou **douchette USB** (optionnel pour les tests)
- **Connexion Internet** (pour Open Food Facts — le scan offline fonctionne aussi)

---

## 🚀 Installation

### Méthode rapide (Windows)

```bash
# Double-cliquez simplement sur :
start.bat
```

Le script crée automatiquement l'environnement virtuel, installe les dépendances et lance le serveur.

### Méthode manuelle

```bash
# 1. Cloner le dépôt
git clone https://github.com/fablabloritz-coder/FriScan.git
cd FriScan

# 2. Créer l'environnement virtuel
python -m venv venv

# 3. Activer l'environnement
venv\Scripts\activate        # Windows (CMD)
venv\Scripts\Activate.ps1    # Windows (PowerShell)
source venv/bin/activate     # Linux/macOS

# 4. Installer les dépendances
pip install -r requirements.txt

# 5. Lancer le serveur
python -m uvicorn server.app:app --reload --host 0.0.0.0 --port 8000
```

### Accéder à l'application

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | Interface principale |
| `http://localhost:8000/docs` | Documentation API (Swagger UI) |
| `http://<ip-local>:8000` | Accès depuis un autre appareil sur le réseau |

---

## 📱 Utilisation

### 1. Scanner un produit

1. Ouvrez l'onglet **Scanner**
2. Choisissez votre méthode :
   - **Webcam** : cliquez "Démarrer la caméra" → présentez le code-barres → cliquez "Scanner"
   - **Douchette USB** : cliquez dans le champ texte → scannez avec la douchette
   - **Manuel** : tapez le code-barres dans le champ
3. Le produit est automatiquement recherché sur Open Food Facts

### 2. Ajouter la date de péremption

- **Vocalement** : cliquez 🎤 et dites la date ("vingt-cinq mars deux mille vingt-six")
- **Manuellement** : utilisez le calendrier tactile (gros boutons, facile au doigt)

### 3. Gérer le frigo

- Consultez la liste de vos produits dans l'onglet **Mon Frigo**
- Filtrez par état : tous, dans le frigo, bientôt périmés, périmés
- Modifiez la quantité ou supprimez des produits

### 4. Obtenir des recettes

- Allez dans l'onglet **Recettes**
- Cliquez "Générer des suggestions"
- Les recettes sont triées par pertinence (produits disponibles + péremption proche)

---

## 📁 Structure du projet

```
FriScan/
├── 📄 README.md                 # Ce fichier
├── 📄 LICENSE                   # Licence MIT
├── 📄 CONTRIBUTING.md           # Guide de contribution
├── 📄 CHANGELOG.md              # Historique des changements
├── 📄 SECURITY.md               # Politique de sécurité
├── 📄 CODE_OF_CONDUCT.md        # Code de conduite
├── 📄 requirements.txt          # Dépendances Python
├── 📄 start.bat                 # Lancement rapide (Windows)
├── 📄 .gitignore                # Fichiers ignorés par Git
│
├── 📂 server/                   # Backend FastAPI
│   ├── app.py                   # Point d'entrée FastAPI
│   ├── database.py              # Configuration SQLite
│   ├── models.py                # Modèles de données
│   ├── 📂 routers/
│   │   ├── products.py          # CRUD produits
│   │   ├── scanner.py           # Endpoint scan barcode
│   │   ├── recipes.py           # Suggestions recettes
│   │   └── fresh_products.py    # Produits frais (sans barcode)
│   ├── 📂 services/
│   │   ├── openfoodfacts.py     # Client API Open Food Facts
│   │   ├── barcode.py           # Logique scan barcode
│   │   └── recipe_engine.py     # Moteur de suggestions
│   └── 📂 data/
│       ├── fresh_products.json  # Base de produits frais
│       └── recipes.json         # Base de recettes locale
│
├── 📂 static/                   # Frontend (interface tactile)
│   ├── index.html               # Page principale
│   ├── 📂 css/
│   │   └── style.css            # Styles (optimisés tactile)
│   └── 📂 js/
│       ├── app.js               # Logique principale
│       ├── scanner.js           # Module scanner webcam
│       └── voice.js             # Module reconnaissance vocale
│
├── 📂 docs/                     # Documentation
│   └── ARCHITECTURE.md          # Architecture technique détaillée
│
└── 📂 .github/                  # Configuration GitHub
    ├── 📂 workflows/
    │   └── ci.yml               # Intégration continue
    ├── 📂 ISSUE_TEMPLATE/
    │   ├── bug_report.md        # Template rapport de bug
    │   └── feature_request.md   # Template demande de fonctionnalité
    └── PULL_REQUEST_TEMPLATE.md # Template pull request
```

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! Consultez le [Guide de contribution](CONTRIBUTING.md) pour commencer.

1. **Fork** le projet
2. Créez votre branche (`git checkout -b feature/ma-fonctionnalite`)
3. **Commit** vos changements (`git commit -m 'Ajout de ma fonctionnalité'`)
4. **Push** sur la branche (`git push origin feature/ma-fonctionnalite`)
5. Ouvrez une **Pull Request**

---

## 📝 Changelog

Voir [CHANGELOG.md](CHANGELOG.md) pour l'historique complet des versions.

---

## 🔒 Sécurité

Si vous découvrez une vulnérabilité, consultez [SECURITY.md](SECURITY.md) pour les instructions de signalement.

---

## 📜 Licence

Ce projet est sous licence **MIT** — voir le fichier [LICENSE](LICENSE) pour plus de détails.

Libre d'utilisation, modification et distribution.

---

## 🙏 Remerciements

- [Open Food Facts](https://world.openfoodfacts.org/) — Base de données produits alimentaires ouverte
- [FastAPI](https://fastapi.tiangolo.com/) — Framework web Python moderne
- [pyzbar](https://github.com/NaturalHistoryMuseum/pyzbar) — Décodeur de codes-barres
- Icônes emoji natives pour une interface légère et universelle

---

<p align="center">
  Développé avec ❤️ au <strong>FabLab Loritz</strong>
</p>
