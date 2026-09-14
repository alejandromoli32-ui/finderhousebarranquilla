import json
import re

with open('data/inmuebles_barranquilla.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for p in data:
    wa = p.get('contact', {}).get('whatsapp', '')
    if wa and not re.match(r'^573\d{9}$', wa):
        print(f"Listing {p['id']}: wa='{wa}', phone='{p.get('contact', {}).get('phone')}'")
