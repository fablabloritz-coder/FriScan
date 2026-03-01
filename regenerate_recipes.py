#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Régénère le fichier marmiton_fallback.json avec:
1. Encodage UTF-8 correct
2. Images uniques pour chaque recette (URLs Wikimedia)
"""

import json
from pathlib import Path

# Mapping unique d'images pour chaque recette
RECIPE_IMAGES = {
    "Ratatouille": "https://commons.wikimedia.org/wiki/Special:FilePath/Ratatouille_3.jpg",
    "Pâtes Aglio e Olio": "https://commons.wikimedia.org/wiki/Special:FilePath/Pasta_aglio_e_olio.jpg",
    "Salade de Tomates et Concombre": "https://commons.wikimedia.org/wiki/Special:FilePath/Salad_vegetables.jpg",
    "Riz aux Légumes": "https://commons.wikimedia.org/wiki/Special:FilePath/Fried_rice.jpg",
    "Soupe de Légumes": "https://commons.wikimedia.org/wiki/Special:FilePath/Vegetable_soup.jpg",
    "Poêlée de Champignons": "https://commons.wikimedia.org/wiki/Special:FilePath/Mushroom_dish.jpg",
    "Pâtes Tomate et Basilic": "https://commons.wikimedia.org/wiki/Special:FilePath/Spaghetti_tomato_basil.jpg",
    "Légumes Rôtis": "https://commons.wikimedia.org/wiki/Special:FilePath/Roasted_vegetables.jpg",
    "Omelette aux Herbes": "https://commons.wikimedia.org/wiki/Special:FilePath/Omelette_herbs.jpg",
    "Pâtes au Pesto de Menthe": "https://commons.wikimedia.org/wiki/Special:FilePath/Pasta_pesto.jpg",
    "Salade de Lentilles": "https://commons.wikimedia.org/wiki/Special:FilePath/Lentil_salad.jpg",
    "Risotto aux Champignons": "https://commons.wikimedia.org/wiki/Special:FilePath/Mushroom_risotto.jpg",
    "Salade de Pâtes": "https://commons.wikimedia.org/wiki/Special:FilePath/Pasta_salad.jpg",
    "Poêlée d'Épinards": "https://commons.wikimedia.org/wiki/Special:FilePath/Spinach_saute.jpg",
    "Gratin de Courges": "https://commons.wikimedia.org/wiki/Special:FilePath/Squash_gratin.jpg",
    "Brocoli Rôti": "https://commons.wikimedia.org/wiki/Special:FilePath/Roasted_broccoli.jpg",
    "Soupe Minestrone": "https://commons.wikimedia.org/wiki/Special:FilePath/Minestrone_soup.jpg",
    "Couscous aux Légumes": "https://commons.wikimedia.org/wiki/Special:FilePath/Couscous_vegetables.jpg",
    "Quiche aux Poireaux": "https://commons.wikimedia.org/wiki/Special:FilePath/Leek_quiche.jpg",
    "Lentilles aux Épices": "https://commons.wikimedia.org/wiki/Special:FilePath/Spiced_lentils.jpg",
    "Tofu Sauté aux Légumes": "https://commons.wikimedia.org/wiki/Special:FilePath/Tofu_stir_fry.jpg",
    "Carottes Miel Thym": "https://commons.wikimedia.org/wiki/Special:FilePath/Honey_glazed_carrots.jpg",
    "Pâtes Tomate Cerises": "https://commons.wikimedia.org/wiki/Special:FilePath/Cherry_tomato_pasta.jpg",
    "Broccoli Amande Rôti": "https://commons.wikimedia.org/wiki/Special:FilePath/Almond_broccoli.jpg",
    "Lentilles Corail Rapides": "https://commons.wikimedia.org/wiki/Special:FilePath/Red_lentil_curry.jpg",
    "Riz Basmati Épicé": "https://commons.wikimedia.org/wiki/Special:FilePath/Basmati_rice_spiced.jpg",
    "Poivrons Rouges Farcis": "https://commons.wikimedia.org/wiki/Special:FilePath/Stuffed_peppers.jpg",
    "Aubergines Grillées": "https://commons.wikimedia.org/wiki/Special:FilePath/Grilled_eggplant.jpg",
    "Haricots Verts Ail": "https://commons.wikimedia.org/wiki/Special:FilePath/Green_beans_garlic.jpg",
    "Chou Farci Végé": "https://commons.wikimedia.org/wiki/Special:FilePath/Vegetable_cabbage_roll.jpg",
    "Pois Chiches Rôtis": "https://commons.wikimedia.org/wiki/Special:FilePath/Roasted_chickpeas.jpg",
    "Sweet Potato Rôti": "https://commons.wikimedia.org/wiki/Special:FilePath/Sweet_potato_roast.jpg",
    "Betteraves Rôties": "https://commons.wikimedia.org/wiki/Special:FilePath/Roasted_beets.jpg",
    "Champignons Portobello": "https://commons.wikimedia.org/wiki/Special:FilePath/Portobello_mushrooms.jpg",
    "Asperges Parmesan": "https://commons.wikimedia.org/wiki/Special:FilePath/Asparagus_parmesan.jpg",
    "Endives Braisées": "https://commons.wikimedia.org/wiki/Special:FilePath/Braised_endives.jpg",
    "Fenouil Rôti": "https://commons.wikimedia.org/wiki/Special:FilePath/Roasted_fennel.jpg",
    "Artichaut Citron": "https://commons.wikimedia.org/wiki/Special:FilePath/Artichoke_lemon.jpg",
    "Navets Moutarde": "https://commons.wikimedia.org/wiki/Special:FilePath/Turnips_mustard.jpg",
    "Radis Beurre": "https://commons.wikimedia.org/wiki/Special:FilePath/Radish_butter.jpg",
    "Champignons Ail Persil": "https://commons.wikimedia.org/wiki/Special:FilePath/Mushrooms_parsley.jpg",
    "Oignons Rouges Vinaigre": "https://commons.wikimedia.org/wiki/Special:FilePath/Red_onions_vinegar.jpg",
    "Courgettes Farcies": "https://commons.wikimedia.org/wiki/Special:FilePath/Stuffed_zucchini.jpg",
    "Salade Grecque": "https://commons.wikimedia.org/wiki/Special:FilePath/Greek_salad.jpg",
    "Taboulé": "https://commons.wikimedia.org/wiki/Special:FilePath/Tabbouleh.jpg",
}

# Données de base des recettes (sans les images corruptes)
recipes_raw = [
    {
        "title": "Ratatouille",
        "difficulty": "moyen",
        "prep_time": 20,
        "cook_time": 40,
        "servings": 4,
        "ingredients": ["2 aubergines", "2 courgettes", "2 poivrons rouges", "4 tomates", "2 oignons", "3 gousses d'ail", "Huile d'olive", "Thym", "Sel et poivre"],
        "steps": ["Découper les légumes", "Faire revenir l'oignon et l'ail", "Ajouter progressivement les légumes", "Ajouter le thym", "Laisser cuire 40 minutes", "Assaisonner et servir"],
        "tags": ["Végétarien", "Légumes", "Français"]
    },
    {
        "title": "Pâtes Aglio e Olio",
        "difficulty": "facile",
        "prep_time": 5,
        "cook_time": 10,
        "servings": 4,
        "ingredients": ["400g de pâtes", "10 gousses d'ail", "150ml d'huile d'olive", "Flocons de piment", "Persil frais", "Sel"],
        "steps": ["Cuire les pâtes", "Faire revenir l'ail dans l'huile", "Égoutter les pâtes", "Mélanger", "Parsemer de persil", "Servir"],
        "tags": ["Pâtes", "Végétarien", "Italien", "Rapide"]
    },
    {
        "title": "Salade de Tomates et Concombre",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 0,
        "servings": 4,
        "ingredients": ["4 tomates", "1 concombre", "1 oignon rouge", "Olives noires", "Huile d'olive", "Vinaigre", "Sel et poivre"],
        "steps": ["Découper les tomates et le concombre", "Ajouter l'oignon et les olives", "Verser l'huile et le vinaigre", "Mélanger et servir"],
        "tags": ["Salade", "Végétarien", "Été", "Léger"]
    },
    {
        "title": "Riz aux Légumes",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 20,
        "servings": 4,
        "ingredients": ["300g de riz", "200g de carottes", "150g de pois", "1 oignon", "2 gousses d'ail", "Bouillon de légumes", "Huile d'olive", "Sel et poivre"],
        "steps": ["Faire revenir l'oignon et l'ail", "Ajouter le riz et mélanger", "Ajouter le bouillon", "Ajouter les légumes à mi-cuisson", "Cuire 15-20 minutes", "Servir"],
        "tags": ["Riz", "Végétarien", "Facile", "Complet"]
    },
    {
        "title": "Soupe de Légumes",
        "difficulty": "facile",
        "prep_time": 15,
        "cook_time": 30,
        "servings": 4,
        "ingredients": ["2 carottes", "2 courgettes", "1 oignon", "4 tomates", "1L de bouillon", "Persil", "Sel et poivre"],
        "steps": ["Émincer les légumes", "Faire revenir l'oignon", "Ajouter les légumes", "Verser le bouillon", "Cuire 25-30 minutes", "Servir chaud"],
        "tags": ["Soupe", "Végétarien", "Réconfortant"]
    },
    {
        "title": "Poêlée de Champignons",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 15,
        "servings": 4,
        "ingredients": ["500g de champignons", "2 oignons", "2 gousses d'ail", "Huile d'olive", "Thym", "Persil", "Sel et poivre"],
        "steps": ["Nettoyer les champignons", "Faire revenir l'oignon et l'ail", "Ajouter les champignons", "Ajouter le thym", "Cuire 10-12 minutes", "Servir"],
        "tags": ["Champignons", "Végétarien", "Entrée", "Français"]
    },
    {
        "title": "Pâtes Tomate et Basilic",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 15,
        "servings": 4,
        "ingredients": ["400g de pâtes", "400g de tomates", "4 gousses d'ail", "Basilic frais", "Huile d'olive", "Sel et poivre"],
        "steps": ["Cuire les pâtes", "Faire revenir l'ail", "Ajouter les tomates", "Cuire 10 minutes", "Ajouter le basilic", "Mélanger et servir"],
        "tags": ["Pâtes", "Tomate", "Végétarien", "Italien"]
    },
    {
        "title": "Légumes Rôtis",
        "difficulty": "facile",
        "prep_time": 15,
        "cook_time": 30,
        "servings": 4,
        "ingredients": ["2 poivrons", "2 aubergines", "2 courgettes", "2 oignons", "Huile d'olive", "Thym et romarin", "Sel et poivre"],
        "steps": ["Découper les légumes", "Les disposer sur une plaque", "Arroser d'huile", "Ajouter les herbes", "Rôtir 25-30 minutes", "Servir chaud ou froid"],
        "tags": ["Légumes", "Végétarien", "Rôti", "Complet"]
    },
    {
        "title": "Omelette aux Herbes",
        "difficulty": "facile",
        "prep_time": 5,
        "cook_time": 5,
        "servings": 2,
        "ingredients": ["4 œufs", "Persil frais", "Ciboulette", "Estragon", "Huile d'olive", "Sel et poivre"],
        "steps": ["Battre les œufs", "Ajouter les fines herbes", "Faire chauffer l'huile", "Verser les œufs", "Plier l'omelette", "Servir"],
        "tags": ["Œufs", "Rapide", "Petit-déjeuner", "Français"]
    },
    {
        "title": "Pâtes au Pesto de Menthe",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 10,
        "servings": 4,
        "ingredients": ["400g de pâtes", "200g de menthe fraîche", "100g de noix", "3 gousses d'ail", "Huile d'olive", "Sel et poivre"],
        "steps": ["Préparer le pesto avec menthe, ail et noix", "Cuire les pâtes", "Mélanger avec le pesto", "Verser l'huile", "Servir"],
        "tags": ["Pâtes", "Végétarien", "Frais", "Rapide"]
    },
    {
        "title": "Salade de Lentilles",
        "difficulty": "facile",
        "prep_time": 15,
        "cook_time": 25,
        "servings": 4,
        "ingredients": ["250g de lentilles corail", "1 oignon rouge", "1 concombre", "2 tomates", "Huile d'olive", "Vinaigre", "Herbes", "Sel et poivre"],
        "steps": ["Cuire les lentilles", "Découper les légumes", "Mélanger les lentilles et légumes", "Préparer la vinaigrette", "Verser et mélanger", "Servir froid"],
        "tags": ["Salade", "Lentilles", "Végétarien", "Protéines"]
    },
    {
        "title": "Risotto aux Champignons",
        "difficulty": "moyen",
        "prep_time": 15,
        "cook_time": 25,
        "servings": 4,
        "ingredients": ["300g de riz arborio", "300g de champignons", "1L de bouillon chaud", "1 oignon", "100ml de vin blanc", "Huile d'olive", "Sel et poivre"],
        "steps": ["Faire revenir l'oignon", "Ajouter le riz et mélanger", "Verser le vin", "Ajouter progressivement le bouillon", "Ajouter les champignons", "Cuire jusqu'à crémeux", "Servir"],
        "tags": ["Riz", "Élégant", "Végétarien", "Français"]
    },
    {
        "title": "Salade de Pâtes",
        "difficulty": "facile",
        "prep_time": 15,
        "cook_time": 10,
        "servings": 4,
        "ingredients": ["300g de pâtes courtes", "200g de tomates cerises", "1 concombre", "100g d'olives", "Roquette", "Huile d'olive", "Vinaigre", "Sel et poivre"],
        "steps": ["Cuire et refroidir les pâtes", "Découper les légumes", "Mélanger tous les ingrédients", "Préparer la vinaigrette", "Verser et mélanger", "Servir"],
        "tags": ["Salade", "Pâtes", "Végétarien", "Été"]
    },
    {
        "title": "Poêlée d'Épinards",
        "difficulty": "facile",
        "prep_time": 5,
        "cook_time": 10,
        "servings": 4,
        "ingredients": ["400g d'épinards frais", "2 gousses d'ail", "1 oignon", "Huile d'olive", "Sel, poivre et muscade"],
        "steps": ["Faire revenir l'oignon et l'ail", "Ajouter les épinards", "Cuire jusqu'à tendres", "Assaisonner avec muscade", "Servir chaud"],
        "tags": ["Épinards", "Légumes", "Végétarien", "Rapide"]
    },
    {
        "title": "Gratin de Courges",
        "difficulty": "moyen",
        "prep_time": 20,
        "cook_time": 45,
        "servings": 6,
        "ingredients": ["1kg de courges", "300ml de bouillon", "2 oignons", "2 gousses d'ail", "Thym et romarin", "Huile d'olive", "Sel et poivre"],
        "steps": ["Découper la courge", "Faire revenir oignon et ail", "Disposer la courge", "Verser le bouillon", "Ajouter les herbes", "Rôtir 40-45 minutes", "Servir chaud"],
        "tags": ["Courges", "Automne", "Végétarien", "Réconfortant"]
    },
    {
        "title": "Brocoli Rôti",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 20,
        "servings": 4,
        "ingredients": ["500g de brocoli", "4 gousses d'ail", "Huile d'olive", "Jus de citron", "Sel et poivre"],
        "steps": ["Tailler le brocoli", "Le mettre sur une plaque", "Arroser d'huile", "Ajouter l'ail", "Rôtir 18-20 minutes", "Verser du citron", "Servir"],
        "tags": ["Brocoli", "Légumes", "Végétarien", "Sain"]
    },
    {
        "title": "Soupe Minestrone",
        "difficulty": "moyen",
        "prep_time": 20,
        "cook_time": 30,
        "servings": 4,
        "ingredients": ["2 carottes", "2 courgettes", "100g de pâtes", "400g de tomates", "1L de bouillon", "Haricots", "Persil", "Sel et poivre"],
        "steps": ["Faire revenir oignon et ail", "Ajouter les légumes", "Verser le bouillon", "Ajouter les pâtes", "Cuire 30 minutes", "Parsemer de persil", "Servir"],
        "tags": ["Soupe", "Complète", "Végétarien", "Italien"]
    },
    {
        "title": "Couscous aux Légumes",
        "difficulty": "facile",
        "prep_time": 15,
        "cook_time": 20,
        "servings": 4,
        "ingredients": ["300g de couscous", "2 carottes", "2 courgettes", "1 oignon", "400ml de bouillon", "Pois chiches", "Huile d'olive", "Sel et poivre"],
        "steps": ["Faire revenir oignon et légumes", "Verser le bouillon", "Ajouter les pois chiches", "Verser sur le couscous", "Laisser reposer 5 min", "Servir"],
        "tags": ["Couscous", "Complet", "Végétarien", "Exotique"]
    },
    {
        "title": "Quiche aux Poireaux",
        "difficulty": "moyen",
        "prep_time": 15,
        "cook_time": 35,
        "servings": 6,
        "ingredients": ["1 pâte brisée", "3 poireaux", "4 œufs", "200ml de crème", "100g de fromage", "Huile d'olive", "Sel et poivre"],
        "steps": ["Nettoyer et trancher les poireaux", "Faire revenir dans l'huile", "Disposer dans la pâte", "Mélanger œufs et crème", "Verser sur les poireaux", "Ajouter le fromage", "Cuire 35 minutes"],
        "tags": ["Quiche", "Poireaux", "Végétarien", "Français"]
    },
    {
        "title": "Lentilles aux Épices",
        "difficulty": "moyen",
        "prep_time": 10,
        "cook_time": 30,
        "servings": 4,
        "ingredients": ["250g de lentilles", "2 oignons", "3 gousses d'ail", "Curry", "Curcuma", "1L de bouillon", "Huile d'olive", "Sel et poivre"],
        "steps": ["Faire revenir oignon et ail avec épices", "Ajouter les lentilles", "Verser le bouillon", "Cuire 30 minutes", "Assaisonner", "Servir chaud"],
        "tags": ["Lentilles", "Épices", "Protéines", "Indien"]
    },
    {
        "title": "Tofu Sauté aux Légumes",
        "difficulty": "facile",
        "prep_time": 15,
        "cook_time": 15,
        "servings": 4,
        "ingredients": ["400g de tofu", "2 poivrons", "200g de brocoli", "2 carottes", "3 gousses d'ail", "Sauce soja", "Huile d'olive", "Gingembre"],
        "steps": ["Découper le tofu en cubes", "Faire revenir le tofu", "Ajouter les légumes", "Ajouter l'ail et le gingembre", "Verser la sauce soja", "Cuire 10 minutes", "Servir"],
        "tags": ["Tofu", "Sauté", "Végétarien", "Asiatique"]
    },
    {
        "title": "Carottes Miel Thym",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 25,
        "servings": 4,
        "ingredients": ["600g de carottes", "3 cuillères de miel", "2 cuillères de vinaigre", "Thym frais", "Huile d'olive", "Sel et poivre"],
        "steps": ["Découper les carottes", "Les mettre sur une plaque", "Mélanger miel et vinaigre", "Verser sur les carottes", "Ajouter le thym", "Rôtir 25 minutes", "Servir"],
        "tags": ["Carottes", "Miel", "Végétarien", "Doux-salé"]
    },
    {
        "title": "Pâtes Tomate Cerises",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 15,
        "servings": 4,
        "ingredients": ["400g de pâtes", "300g de tomates cerises", "4 gousses d'ail", "Basilic frais", "Huile d'olive", "Sel et poivre"],
        "steps": ["Cuire les pâtes", "Faire revenir l'ail", "Ajouter les tomates cerises", "Cuire jusqu'à fondre", "Ajouter le basilic", "Mélanger avec les pâtes", "Servir"],
        "tags": ["Pâtes", "Tomates", "Végétarien", "Rapide"]
    },
    {
        "title": "Broccoli Amande Rôti",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 20,
        "servings": 4,
        "ingredients": ["500g de brocoli", "100g d'amandes", "4 gousses d'ail", "Huile d'olive", "Sel et poivre"],
        "steps": ["Tailler le brocoli", "Torréfier les amandes", "Mettre le tout sur une plaque", "Arroser d'huile", "Ajouter l'ail", "Rôtir 20 minutes", "Mélanger et servir"],
        "tags": ["Brocoli", "Amandes", "Végétarien", "Protéiné"]
    },
    {
        "title": "Lentilles Corail Rapides",
        "difficulty": "facile",
        "prep_time": 5,
        "cook_time": 25,
        "servings": 4,
        "ingredients": ["250g de lentilles corail", "250ml de bouillon", "1 oignon", "2 tomates", "Curry", "Huile d'olive", "Sel et poivre"],
        "steps": ["Faire revenir l'oignon", "Ajouter les lentilles", "Verser le bouillon", "Ajouter les tomates", "Ajouter le curry", "Cuire 20-25 minutes", "Servir"],
        "tags": ["Lentilles", "Rapide", "Protéines", "Épicé"]
    },
    {
        "title": "Riz Basmati Épicé",
        "difficulty": "facile",
        "prep_time": 5,
        "cook_time": 20,
        "servings": 4,
        "ingredients": ["300g de riz basmati", "500ml de bouillon", "1 oignon", "2 tomates", "Curcuma", "Cumin", "Huile d'olive", "Sel"],
        "steps": ["Faire revenir l'oignon avec épices", "Ajouter le riz", "Verser le bouillon", "Ajouter les tomates", "Cuire 18-20 minutes", "Servir"],
        "tags": ["Riz", "Basmati", "Épicé", "Complet"]
    },
    {
        "title": "Poivrons Rouges Farcis",
        "difficulty": "moyen",
        "prep_time": 20,
        "cook_time": 30,
        "servings": 4,
        "ingredients": ["4 poivrons rouges", "300g de riz", "1 oignon", "400g de tomates", "Persil", "Huile d'olive", "Sel et poivre"],
        "steps": ["Évider les poivrons", "Préparer la farce avec riz et oignon", "Remplir les poivrons", "Les mettre dans un plat", "Verser les tomates", "Cuire 30 minutes", "Servir chaud"],
        "tags": ["Poivrons", "Farci", "Végétarien", "Complet"]
    },
    {
        "title": "Aubergines Grillées",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 15,
        "servings": 4,
        "ingredients": ["2 aubergines", "4 gousses d'ail", "Huile d'olive", "Vinaigre balsamique", "Persil frais", "Sel et poivre"],
        "steps": ["Trancher les aubergines", "Les badigeonner d'huile", "Les griller ou rôtir", "Les arroser de vinaigre", "Saupoudrer d'ail", "Parsemer de persil", "Servir"],
        "tags": ["Aubergines", "Grillé", "Végétarien", "Méditerranéen"]
    },
    {
        "title": "Haricots Verts Ail",
        "difficulty": "facile",
        "prep_time": 5,
        "cook_time": 15,
        "servings": 4,
        "ingredients": ["500g de haricots verts", "4 gousses d'ail", "Huile d'olive", "Citron", "Sel et poivre"],
        "steps": ["Blanchir les haricots", "Faire revenir l'ail dans l'huile", "Ajouter les haricots", "Cuire 5 minutes", "Ajouter du citron", "Servir"],
        "tags": ["Haricots", "Ail", "Végétarien", "Léger"]
    },
    {
        "title": "Chou Farci Végé",
        "difficulty": "moyen",
        "prep_time": 25,
        "cook_time": 45,
        "servings": 6,
        "ingredients": ["1 chou", "300g de riz", "2 oignons", "2 tomates", "Herbes", "Huile d'olive", "Sel et poivre"],
        "steps": ["Blanchir les feuilles de chou", "Préparer la farce riz-oignon", "Remplir les feuilles", "Les disposer dans un plat", "Verser du bouillon", "Cuire 45 minutes", "Servir"],
        "tags": ["Chou", "Farci", "Végétarien", "Traditionnel"]
    },
    {
        "title": "Pois Chiches Rôtis",
        "difficulty": "facile",
        "prep_time": 5,
        "cook_time": 30,
        "servings": 4,
        "ingredients": ["400g de pois chiches", "Paprika", "Cumin", "Huile d'olive", "Sel"],
        "steps": ["Égoutter et sécher les pois chiches", "Les badigeonner d'huile", "Ajouter épices", "Les mettre sur une plaque", "Rôtir 25-30 minutes", "Servir"],
        "tags": ["Pois chiches", "Rôti", "Végétarien", "Snack"]
    },
    {
        "title": "Sweet Potato Rôti",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 25,
        "servings": 4,
        "ingredients": ["600g de patates douces", "2 cuillères de miel", "Paprika", "Huile d'olive", "Sel et poivre"],
        "steps": ["Découper les patates en bâtons", "Les mettre sur une plaque", "Badigeonner d'huile et miel", "Ajouter la paprika", "Rôtir 25 minutes", "Servir"],
        "tags": ["Patates", "Rôti", "Végétarien", "Sucré-salé"]
    },
    {
        "title": "Betteraves Rôties",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 45,
        "servings": 4,
        "ingredients": ["500g de betteraves", "Huile d'olive", "Vinaigre", "Thym", "Sel et poivre"],
        "steps": ["Découper les betteraves", "Les mettre sur une plaque", "Badigeonner d'huile", "Ajouter le thym", "Rôtir 45 minutes", "Arroser de vinaigre", "Servir"],
        "tags": ["Betteraves", "Rôti", "Végétarien", "Sucré"]
    },
    {
        "title": "Champignons Portobello",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 20,
        "servings": 4,
        "ingredients": ["4 champignons portobello", "4 gousses d'ail", "Huile d'olive", "Persil", "Citron", "Sel et poivre"],
        "steps": ["Nettoyer les champignons", "Les badigeonner d'huile", "Ajouter l'ail émincé", "Rôtir ou griller 20 minutes", "Garnir de persil", "Servir avec citron"],
        "tags": ["Champignons", "Portobello", "Végétarien", "Élégant"]
    },
    {
        "title": "Asperges Parmesan",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 15,
        "servings": 4,
        "ingredients": ["500g d'asperges", "100g de parmesan", "Huile d'olive", "Citron", "Sel et poivre"],
        "steps": ["Nettoyer les asperges", "Les mettre sur une plaque", "Badigeonner d'huile", "Rôtir 15 minutes", "Râper le parmesan dessus", "Servir avec citron"],
        "tags": ["Asperges", "Parmesan", "Végétarien", "Française"]
    },
    {
        "title": "Endives Braisées",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 25,
        "servings": 4,
        "ingredients": ["8 endives", "1 oignon", "250ml de bouillon", "Huile d'olive", "Citron", "Sel et poivre"],
        "steps": ["Nettoyer les endives", "Faire revenir l'oignon", "Disposer les endives", "Verser le bouillon", "Braiser 25 minutes", "Servir avec citron"],
        "tags": ["Endives", "Braisé", "Végétarien", "Français"]
    },
    {
        "title": "Fenouil Rôti",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 30,
        "servings": 4,
        "ingredients": ["2 bulbes de fenouil", "Huile d'olive", "Citron", "Thym", "Sel et poivre"],
        "steps": ["Découper le fenouil", "Le mettre sur une plaque", "Badigeonner d'huile", "Ajouter le thym", "Rôtir 30 minutes", "Servir avec citron"],
        "tags": ["Fenouil", "Rôti", "Végétarien", "Léger"]
    },
    {
        "title": "Artichaut Citron",
        "difficulty": "moyen",
        "prep_time": 15,
        "cook_time": 30,
        "servings": 4,
        "ingredients": ["4 artichauts", "2 citrons", "4 gousses d'ail", "Huile d'olive", "Estragon", "Sel et poivre"],
        "steps": ["Préparer les artichauts", "Mélanger huile, citron et ail", "Les tremper dedans", "Cuire à la vapeur 30 min", "Servir avec sauce", "Garnir d'estragon"],
        "tags": ["Artichaut", "Citron", "Végétarien", "Élégant"]
    },
    {
        "title": "Navets Moutarde",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 25,
        "servings": 4,
        "ingredients": ["600g de navets", "2 cuillères de moutarde", "1 oignon", "Huile d'olive", "Miel", "Sel et poivre"],
        "steps": ["Découper les navets", "Faire revenir l'oignon", "Ajouter les navets", "Verser moutarde et miel", "Cuire 25 minutes", "Servir"],
        "tags": ["Navets", "Moutarde", "Végétarien", "Savoureux"]
    },
    {
        "title": "Radis Beurre",
        "difficulty": "facile",
        "prep_time": 5,
        "cook_time": 0,
        "servings": 4,
        "ingredients": ["400g de radis", "100g de beurre", "Sel fin", "Persil", "Pain grillé"],
        "steps": ["Nettoyer les radis", "Les disposer dans une assiette", "Mettre beurre à côté", "Servir avec sel et pain"],
        "tags": ["Radis", "Cru", "Végétarien", "Aperitif"]
    },
    {
        "title": "Champignons Ail Persil",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 15,
        "servings": 4,
        "ingredients": ["500g de champignons de Paris", "6 gousses d'ail", "100ml de vin blanc", "Persil frais", "Huile d'olive", "Sel et poivre"],
        "steps": ["Nettoyer les champignons", "Faire revenir l'ail", "Ajouter les champignons", "Verser le vin blanc", "Cuire 15 minutes", "Garnir de persil", "Servir"],
        "tags": ["Champignons", "Ail", "Végétarien", "Français"]
    },
    {
        "title": "Oignons Rouges Vinaigre",
        "difficulty": "facile",
        "prep_time": 10,
        "cook_time": 0,
        "servings": 4,
        "ingredients": ["500g d'oignons rouges", "100ml de vinaigre", "100ml d'eau", "Sucre", "Epices", "Sel"],
        "steps": ["Trancher finement les oignons", "Les mettre dans un bocal", "Verser vinaigre et eau", "Ajouter sucre et épices", "Laisser marinée", "Servir"],
        "tags": ["Oignons", "Mariné", "Végétarien", "Condiment"]
    },
    {
        "title": "Courgettes Farcies",
        "difficulty": "moyen",
        "prep_time": 20,
        "cook_time": 30,
        "servings": 4,
        "ingredients": ["4 courgettes", "300g de riz", "1 oignon", "2 tomates", "Herbes", "Huile d'olive", "Sel et poivre"],
        "steps": ["Dimidier les courgettes", "Réserver la chair", "Préparer la farce", "Remplir les courgettes", "Les disposer dans un plat", "Cuire 30 minutes", "Servir"],
        "tags": ["Courgettes", "Farci", "Végétarien", "Été"]
    },
    {
        "title": "Salade Grecque",
        "difficulty": "facile",
        "prep_time": 15,
        "cook_time": 0,
        "servings": 4,
        "ingredients": ["3 tomates", "1 concombre", "100g de feta", "100g d'olives", "1 oignon rouge", "Huile d'olive", "Vinaigre", "Origan"],
        "steps": ["Découper tous les légumes", "Les mettre dans un saladier", "Ajouter la feta équarries", "Ajouter les olives", "Verser huile et vinaigre", "Saupoudrer d'origan", "Servir"],
        "tags": ["Salade", "Grecque", "Végétarien", "Méditerranéen"]
    },
    {
        "title": "Taboulé",
        "difficulty": "facile",
        "prep_time": 15,
        "cook_time": 0,
        "servings": 4,
        "ingredients": ["250g de boulghour", "300ml d'eau chaude", "1 botte de persil", "Tomates", "Concombre", "Oignon", "Citron", "Huile d'olive"],
        "steps": ["Verser eau chaude sur boulghour", "Laisser reposer 15 min", "Hacher finement le persil", "Découper les légumes", "Mélanger avec boulghour", "Ajouter citron et huile", "Servir"],
        "tags": ["Taboulé", "Boulghour", "Végétarien", "Moyen-Oriental"]
    },
]

print("🔧 Régénération du fichier marmiton_fallback.json...")
print(f"📝 Traitement de {len(recipes_raw)} recettes...\n")

# Ajouter les images à chaque recette
recipes_final = []
for recipe in recipes_raw:
    # Récupérer l'image
    title = recipe.get("title", "")
    image_url = RECIPE_IMAGES.get(title, "")
    
    recipe["image_url"] = image_url
    recipes_final.append(recipe)
    
    if image_url:
        print(f"✓ {title}")
    else:
        print(f"⚠️  {title} (image générique)")

# Sauvegarder en JSON avec encodage UTF-8 correct
json_file = Path('server/data/marmiton_fallback.json')
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(recipes_final, f, ensure_ascii=False, indent=2)

print(f"\n✅ {len(recipes_final)} recettes sauvegardées")
print(f"📄 Fichier: {json_file}")
print(f"🔤 Encodage: UTF-8 (ensure_ascii=False)")
