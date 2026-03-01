#!/usr/bin/env python3
"""
Test diagnostic pour identifier le problème du frigo
"""
import requests

BASE_URL = "http://localhost:8001"

print("=" * 60)
print("TEST DIAGNOSTIC - ENDPOINT /api/fridge/")
print("=" * 60)

try:
    resp = requests.get(f"{BASE_URL}/api/fridge/", timeout=5)
    print(f"\nStatus: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\nClés retournées: {list(data.keys())}")
        
        # Vérifier ce qui contient les items
        if "data" in data:
            print(f"\n✓ Clé 'data' trouvée: {type(data['data'])} avec {len(data['data'])} éléments")
            if len(data['data']) > 0:
                print(f"  Premier item: {data['data'][0].get('name', 'N/A')}")
        else:
            print(f"\n✗ Clé 'data' absente!")
        
        if "items" in data:
            print(f"\n✓ Clé 'items' trouvée: {type(data['items'])} avec {len(data['items'])} éléments")
            if len(data['items']) > 0:
                print(f"  Premier item: {data['items'][0].get('name', 'N/A')}")
        else:
            print(f"\n✗ Clé 'items' absente!")
        
        print(f"\n📊 Résultat complet:")
        print(f"  success: {data.get('success')}")
        print(f"  total: {data.get('total')}")
        print(f"  count: {data.get('count')}")
        print(f"  page: {data.get('page')}")
        print(f"  pages: {data.get('pages')}")
        
        print(f"\n❌ PROBLÈME IDENTIFIÉ:")
        print(f"  - Backend retourne: 'data'")
        print(f"  - Frontend attend: 'items'")
        print(f"  - Solution: Changer 'data' en 'items' dans le backend")
    else:
        print(f"Erreur: {resp.text}")
        
except Exception as e:
    print(f"Erreur de connexion: {e}")
    print(f"\n⚠️ Assurez-vous que le serveur tourne sur le port 8001")
