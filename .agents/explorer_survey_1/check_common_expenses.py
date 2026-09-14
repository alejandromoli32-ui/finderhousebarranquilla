import json

with open(".agents/explorer_survey_1/fincaraiz_sample_item.json", "r", encoding="utf-8") as f:
    item = json.load(f)

for k in ['commonExpenses', 'commonExpenses_currency', 'ceCurrencyID', 'price_admin_usd', 'include_administration']:
    print(f"{k}: {repr(item.get(k))}")
