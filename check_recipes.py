import json
from pathlib import Path

json_file = Path('server/data/marmiton_fallback.json')
with open(json_file, 'r', encoding='utf-8') as f:
    recipes = json.load(f)

print(f'Statistiques du fichier:')
print(f'  Total recettes: {len(recipes)}')
print(f'  Images uniques: {len(set(r.get("image_url") for r in recipes))}')
print(f'  Fichier: {json_file.stat().st_size / 1024:.1f} KB')
