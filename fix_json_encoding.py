#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path

# Lire le fichier JSON corrompu
json_file = Path('server/data/marmiton_fallback.json')

print("🔧 Réparation du fichier JSON...")

try:
    # Lire avec les encodages possibles
    content = None
    for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            with open(json_file, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"✓ Fichier lu avec encodage: {encoding}")
            break
        except UnicodeDecodeError:
            continue
    
    if not content:
        print("✗ Impossible de lire le fichier")
        exit(1)
    
    # Décoder et ré-encoder correctement
    recipes = json.loads(content)
    
    # Fonction pour corriger un string mal encodé
    def fix_encoding(s):
        if not isinstance(s, str):
            return s
        try:
            # Si déjà bien encodé, retourner tel quel
            return s
        except:
            # Tenter de réparer le double encodage
            try:
                return s.encode('utf-8').decode('utf-8')
            except:
                return s
    
    def fix_dict(obj):
        """Corriger récursivement tous les strings du dictionnaire"""
        if isinstance(obj, dict):
            return {k: fix_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [fix_dict(item) for item in obj]
        elif isinstance(obj, str):
            # Tenter de corriger le string
            try:
                # Essayer d'identifier si c'est du double-encodage
                if 'Ã' in obj or 'â' in obj or '©' in obj:  # Caractères typiques du mal-encodage
                    # C'est probablement du UTF-8 mal décodé en latin-1
                    return obj.encode('latin-1').decode('utf-8')
            except:
                pass
            return obj
        else:
            return obj
    
    recipes = fix_dict(recipes)
    
    # Vérifier quelques titres
    print("\n📋 Exemples de titres corrigés:")
    for i, recipe in enumerate(recipes[:5]):
        print(f"  {i+1}. {recipe.get('title')}")
    
    # Sauvegarder en UTF-8 correct
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ {len(recipes)} recettes réparées et sauvegardées")
    print("   Encodage: UTF-8")
    
except Exception as e:
    print(f"✗ Erreur: {e}")
    import traceback
    traceback.print_exc()
