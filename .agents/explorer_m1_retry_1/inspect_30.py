import sys
sys.path.insert(0, '.')
import json
from collections import Counter
from data_pipeline.deduplicator import normalize_neighborhood
from data_pipeline.pipeline import ALLOWED_BARRIOS

with open('data_pipeline/fallback_data.json', encoding='utf-8') as f:
    raw = json.load(f)

print("=== ALL 30 RAW LISTINGS NOT IN ALLOWED_BARRIOS ===")
for p in raw:
    barrio = p.get('neighborhood', '')
    norm_b = normalize_neighborhood(barrio)
    if norm_b not in ALLOWED_BARRIOS:
        print(f"ID: {p['id']} | Raw: '{barrio}' | Norm: '{norm_b}' | Zone: '{p.get('zone')}' | Title: '{p.get('title')[:35]}'")
