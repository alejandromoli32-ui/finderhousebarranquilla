import sys
sys.path.insert(0, '.')
import json
from data_pipeline.deduplicator import deduplicate_listings, normalize_neighborhood
from data_pipeline.pipeline import ALLOWED_BARRIOS

with open('data_pipeline/fallback_data.json', encoding='utf-8') as f:
    raw = json.load(f)

print('Total raw:', len(raw))

# Candidate 1: Reject external municipalities, but allow Ciudad Mallorquin as an allowed sector
c1 = []
for p in raw:
    text = f"{p.get('title','')} {p.get('neighborhood','')} {p.get('address','')} {p.get('url','')}".lower()
    norm_b = normalize_neighborhood(p.get('neighborhood',''))
    if any(m in text for m in ['soledad', 'malambo', 'galapa', 'baranoa', 'sabanagrande']):
        continue
    if 'puerto colombia' in text or 'puerto_colombia' in text or 'puerto-colombia' in text:
        if norm_b != 'ciudad_mallorquin' and 'mallorquin' not in text:
            continue
    c1.append(p)

d1, s1 = deduplicate_listings(c1)
print(f'Candidate 1 (exception for Ciudad Mallorquin): raw passed = {len(c1)}, deduped = {len(d1)}')

# Candidate 2: Strictly reject ANY listing containing 'puerto colombia'
c2 = []
for p in raw:
    text = f"{p.get('title','')} {p.get('neighborhood','')} {p.get('address','')} {p.get('url','')}".lower()
    if any(m in text for m in ['soledad', 'malambo', 'galapa', 'baranoa', 'sabanagrande', 'puerto colombia', 'puerto_colombia', 'puerto-colombia']):
        continue
    c2.append(p)

d2, s2 = deduplicate_listings(c2)
print(f'Candidate 2 (strict reject any puerto colombia): raw passed = {len(c2)}, deduped = {len(d2)}')

ids1 = {p['id'] for p in d1}
ids2 = {p['id'] for p in d2}
print('In d1 but not d2:', ids1 - ids2)
print('In d2 but not d1:', ids2 - ids1)
