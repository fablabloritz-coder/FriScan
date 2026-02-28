# 📋 Changelog — FriScan

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

---

## [2.0.0] — 2025-06-15

### ✨ Ajouté

- **Interface 100% tactile** : refonte complète CSS pour Surface Pro (min 48px touch targets)
- **Mode plein écran** : bouton toggle fullscreen pour usage tablette
- **Onglet Réglages** : paramétrage des jours d'alerte péremption, régimes, intervalle scan
- **Boutons de quantité tactiles** : presets (100g, 250g, 500g, 1kg, 1L, 1 pièce) + stepper +/-
- **Régimes alimentaires** : filtrage recettes (végétarien, vegan, sans-gluten, sans-lactose)
- **120+ produits frais** : base étendue avec catégories Surgelés, Boissons, Boulangerie, Charcuterie
- **35+ recettes avec tags diététiques** : chaque recette identifie ses compatibilités
- **Multi-caméras** : sélecteur de caméra pour basculer entre webcam/USB
- **Flash/Torche** : toggle pour scanner en conditions de faible luminosité
- **Notes sur produits** : champ notes pour poids/format (ex: 500g, 1L)
- **Péremption configurable** : slider 1-14 jours pour les alertes
- **Filtres de catégorie** : onglets de catégorie dans la grille de produits rapides

### 🔄 Modifié

- Refonte CSS complète : variables CSS, design system cohérent
- Tabs en mode icône + label compact pour économiser l'espace
- Stats bar compacte dans le header
- Grille de recettes avec tags de régime et expandable instructions
- Moteur de recettes accepte filtrage par régime alimentaire
- API /api/recipes/suggestions : nouveaux params `diet` et `expiry_days`
- API /api/products : nouveau filtre `expired=true`, champ `notes`
- Renommage champs stats API pour cohérence frontend

---

## [1.0.0] — 2026-02-28

### ✨ Ajouté

- **Scanner de codes-barres** via webcam (OpenCV + pyzbar)
- **Support douchette USB** avec détection automatique de saisie rapide
- **Changement de caméra** : bascule entre webcam avant/arrière sur Surface Pro
- **Activation flash/torche** pour scanner en conditions de faible luminosité
- **Reconnaissance vocale** des dates de péremption (Web Speech API, français)
- **Calendrier tactile** grand format pour saisie manuelle des dates
- **Recherche Open Food Facts** : récupération automatique des infos produit
- **Gestion produits frais** : ajout manuel de fruits, légumes, viande, etc.
- **Base de recettes locale** : 20+ recettes françaises avec algorithme de suggestion
- **Moteur de suggestions** : correspondance floue, bonus péremption proche
- **Interface tactile** : UI optimisée pour Surface Pro et écrans tactiles
- **Filtres et recherche** : tri par état (frigo, bientôt périmé, périmé)
- **Alertes péremption** : badges visuels pour les produits à consommer rapidement
- **API REST complète** : CRUD produits, scan, recettes (documentée via Swagger)
- **Documentation** : README, ARCHITECTURE.md, guide de contribution
- **Script de démarrage** : `start.bat` pour lancement en un clic sous Windows

### 🏗️ Architecture

- Backend : Python 3.10+ / FastAPI
- Base de données : SQLite via SQLAlchemy ORM
- Frontend : HTML5 / CSS3 / JavaScript vanilla
- Pas de framework frontend (léger, rapide, compatible tablette)

---

## [Unreleased]

### 🔮 Prévu

- [ ] Tests unitaires backend (pytest)
- [ ] Tests E2E frontend
- [ ] Mode hors-ligne complet (cache Open Food Facts)
- [ ] Export de la liste de courses
- [ ] Notifications push via Service Worker
- [ ] Thème sombre
- [ ] Support multi-utilisateur
- [ ] Application PWA installable

---

[1.0.0]: https://github.com/fablabloritz-coder/FriScan/releases/tag/v1.0.0
[Unreleased]: https://github.com/fablabloritz-coder/FriScan/compare/v1.0.0...HEAD
