# 🤝 Guide de Contribution — FriScan

Merci de votre intérêt pour FriScan ! Ce guide vous aidera à contribuer efficacement au projet.

## 📋 Table des matières

- [Code de conduite](#code-de-conduite)
- [Comment contribuer](#comment-contribuer)
- [Signaler un bug](#-signaler-un-bug)
- [Proposer une fonctionnalité](#-proposer-une-fonctionnalité)
- [Soumettre du code](#-soumettre-du-code)
- [Conventions de code](#-conventions-de-code)
- [Structure du projet](#-structure-du-projet)

---

## Code de conduite

En participant à ce projet, vous acceptez de respecter notre [Code de Conduite](CODE_OF_CONDUCT.md). Soyez respectueux et bienveillant.

---

## Comment contribuer

### 🐛 Signaler un bug

1. Vérifiez que le bug n'a pas déjà été signalé dans les [Issues](https://github.com/fablabloritz-coder/FriScan/issues)
2. Créez une nouvelle issue en utilisant le template **Bug Report**
3. Incluez :
   - Les étapes pour reproduire le bug
   - Le comportement attendu vs observé
   - Votre environnement (OS, navigateur, version Python)
   - Des captures d'écran si possible

### 💡 Proposer une fonctionnalité

1. Vérifiez que l'idée n'a pas déjà été proposée
2. Créez une issue avec le template **Feature Request**
3. Décrivez clairement :
   - Le problème que vous cherchez à résoudre
   - La solution que vous proposez
   - Les alternatives envisagées

### 🔧 Soumettre du code

#### Prérequis

- Python 3.10+
- Git
- Un éditeur de code (VS Code recommandé)

#### Workflow

1. **Fork** le dépôt sur GitHub
2. **Clonez** votre fork :
   ```bash
   git clone https://github.com/<votre-username>/FriScan.git
   cd FriScan
   ```
3. **Créez une branche** pour votre modification :
   ```bash
   git checkout -b feature/ma-fonctionnalite
   # ou
   git checkout -b fix/correction-du-bug
   ```
4. **Installez l'environnement** de développement :
   ```bash
   python -m venv venv
   venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   ```
5. **Faites vos modifications** et testez-les
6. **Commitez** avec un message clair :
   ```bash
   git add .
   git commit -m "feat: ajout du support multi-caméra"
   ```
7. **Poussez** vers votre fork :
   ```bash
   git push origin feature/ma-fonctionnalite
   ```
8. **Ouvrez une Pull Request** vers la branche `main` du dépôt principal

---

## 📏 Conventions de code

### Python (Backend)

- **Style** : PEP 8
- **Docstrings** : format Google
- **Types** : utiliser les type hints
- **Nommage** :
  - Variables et fonctions : `snake_case`
  - Classes : `PascalCase`
  - Constantes : `UPPER_SNAKE_CASE`

```python
# ✅ Bon
def get_product_by_barcode(barcode: str) -> Optional[ProductDB]:
    """Recherche un produit par code-barres.
    
    Args:
        barcode: Le code-barres à rechercher.
    
    Returns:
        Le produit trouvé ou None.
    """
    ...

# ❌ Mauvais
def getProduct(bc):
    ...
```

### JavaScript (Frontend)

- **Style** : pas de framework, vanilla JS
- **Nommage** : `camelCase` pour les fonctions et variables
- **Commentaires** : en français, clairs et concis
- **DOM** : utiliser `getElementById` / `querySelector`

### HTML/CSS

- **Sémantique** : utiliser les balises HTML5 appropriées
- **Accessibilité** : penser tactile et lisibilité
- **Classes CSS** : nommage descriptif en kebab-case (`btn-primary`, `scan-result`)

### Messages de commit

Suivre la convention [Conventional Commits](https://www.conventionalcommits.org/fr/) :

| Préfixe | Usage |
|---------|-------|
| `feat:` | Nouvelle fonctionnalité |
| `fix:` | Correction de bug |
| `docs:` | Documentation |
| `style:` | Formatage (pas de changement de logique) |
| `refactor:` | Refactoring |
| `test:` | Ajout/modification de tests |
| `chore:` | Maintenance (dépendances, config) |

---

## 📁 Structure du projet

Consultez le [README](README.md#-structure-du-projet) pour la structure complète.

### Points importants

- **Backend** (`server/`) : API FastAPI, ne pas modifier la structure des routers sans discussion
- **Frontend** (`static/`) : HTML/CSS/JS vanilla, pas de framework
- **Données** (`server/data/`) : fichiers JSON de configuration, modifiables librement
- **Documentation** (`docs/`) : à maintenir à jour pour chaque modification

---

## 💬 Questions ?

N'hésitez pas à ouvrir une issue avec le label `question` ou à participer aux discussions.

Merci de contribuer à FriScan ! 🧊
