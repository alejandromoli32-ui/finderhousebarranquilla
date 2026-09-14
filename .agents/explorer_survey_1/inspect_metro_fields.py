import json

with open(".agents/explorer_survey_1/metrocuadrado_sample_item.json", "r", encoding="utf-8") as f:
    sample = json.load(f)

for k, v in sample.items():
    print(f"{k}: {repr(v)[:120]}")

print("\n--- 'data' subfield in sample: ---")
if 'data' in sample and isinstance(sample['data'], dict):
    for k, v in sample['data'].items():
        print(f"data.{k}: {repr(v)[:120]}")
