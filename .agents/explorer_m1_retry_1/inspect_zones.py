import sys
sys.path.insert(0, '.')
import json

with open('data_pipeline/fallback_data.json', encoding='utf-8') as f:
    raw = json.load(f)

for p in raw:
    if p.get('zone') in ['Otros', 'Villa Campestre']:
        print(f"ID: {p['id']} | Zone: '{p.get('zone')}' | Barrio: '{p.get('neighborhood')}' | Title: '{p.get('title')[:40]}'")
