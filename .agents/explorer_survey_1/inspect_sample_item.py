import json

with open(".agents/explorer_survey_1/fincaraiz_sample_item.json", "r", encoding="utf-8") as f:
    item = json.load(f)

print("Sample item keys count:", len(item.keys()))
print("\nSample Item Key Fields:")
for k in ['id', 'title', 'price', 'address', 'link', 'images', 'seller', 'owner', 'technicalSheet', 'description']:
    print(f"--- {k} ---")
    val = item.get(k)
    if isinstance(val, (dict, list)):
        print(json.dumps(val, indent=2)[:500])
    else:
        print(val)
