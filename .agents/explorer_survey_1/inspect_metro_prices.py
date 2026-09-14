import json
import re

with open(".agents/explorer_survey_1/metrocuadrado_rsc.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Search for filter objects or price parameters in Metrocuadrado
for term in ['"priceTo"', '"maxPrice"', '"precioHasta"', '"filters"', '"selectedFilters"', '"priceRange"']:
    matches = [m.start() for m in re.finditer(term, text)]
    print(f"Term {term}: {len(matches)} occurrences")
    for m in matches[:3]:
        print(f"  Snippet: {text[max(0, m-50):m+150]}")

# Let's inspect the prices of all 65 results in Metrocuadrado to see their range
start_idx = text.find('"results":[')
if start_idx != -1:
    array_start = start_idx + len('"results":')
    bracket_count = 0
    end_idx = -1
    for i in range(array_start, len(text)):
        if text[i] == '[':
            bracket_count += 1
        elif text[i] == ']':
            bracket_count -= 1
            if bracket_count == 0:
                end_idx = i + 1
                break
    results = json.loads(text[array_start:end_idx])
    prices = []
    for r in results:
        canon = r.get('mvalorarriendo', 0)
        admin = 0
        try:
            admin_str = r.get('data', {}).get('mvaloradministracion')
            if admin_str:
                admin = float(admin_str)
        except:
            pass
        prices.append((canon, admin, canon + admin, r.get('title'), r.get('mnombrecomunbarrio')))
    
    print(f"\nTotal items: {len(prices)}")
    print(f"Items with total <= 2.500.000 COP: {sum(1 for p in prices if p[2] <= 2500000)}")
    print("First 10 items (Canon, Admin, Total, Title, Barrio):")
    for p in prices[:10]:
        print(f"  Canon: {p[0]:,}, Admin: {p[1]:,}, Total: {p[2]:,} | {p[4]} | {p[3][:40]}")
