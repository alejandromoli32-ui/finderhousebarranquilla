import json

with open(".agents/explorer_survey_1/metrocuadrado_sample_item.json", "r", encoding="utf-8") as f:
    sample = json.load(f)

print("Keys containing 'dir' or 'addr' or 'ubic':")
for k, v in sample.items():
    if any(term in k.lower() for term in ['dir', 'addr', 'ubic', 'nom', 'barrio', 'local']):
        print(f"  {k}: {v}")

print("\nNested 'data' keys:")
for k, v in sample.get('data', {}).items():
    print(f"  data.{k}: {v}")
