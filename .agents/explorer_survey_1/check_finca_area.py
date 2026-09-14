import json

with open(".agents/explorer_survey_1/fincaraiz_sample_item.json", "r", encoding="utf-8") as f:
    item = json.load(f)

for k in ['m2', 'm2Built', 'm2apto', 'm2Terrain', 'm2Terrace']:
    print(f"{k}: {repr(item.get(k))}")

tech = {t.get('field'): (t.get('value'), t.get('text')) for t in item.get('technicalSheet', [])}
print("\nTechnical sheet fields:")
for k, v in tech.items():
    print(f"  {k}: {v}")
