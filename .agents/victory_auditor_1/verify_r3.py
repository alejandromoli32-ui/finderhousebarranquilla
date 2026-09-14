import json
from pathlib import Path

dossier_md_path = Path("DOSSIER_VISITAS.md")
dossier_json_path = Path("data/dossier_curado.json")
database_path = Path("data/inmuebles_barranquilla.json")

assert dossier_md_path.exists(), "DOSSIER_VISITAS.md missing"
assert dossier_json_path.exists(), "data/dossier_curado.json missing"
assert database_path.exists(), "data/inmuebles_barranquilla.json missing"

with open(database_path, encoding="utf-8") as f:
    db = json.load(f)
db_ids = {x["id"]: x for x in db}

with open(dossier_json_path, encoding="utf-8") as f:
    dossier_data = json.load(f)

dossier_items = dossier_data.get("properties", []) if isinstance(dossier_data, dict) else dossier_data
dossier_md = dossier_md_path.read_text(encoding="utf-8")

print(f"Total curated properties in dossier_curado.json: {len(dossier_items)}")
assert 10 <= len(dossier_items) <= 15, f"Expected 10-15 properties, got {len(dossier_items)}"

violations = []
for i, item in enumerate(dossier_items):
    pid = item.get("id")
    if pid not in db_ids:
        violations.append(f"Property {pid} in dossier does not exist in master database")
    
    total = item.get("total_price", 0)
    if total > 2500000:
        violations.append(f"Property {pid}: Total price {total} > 2,500,000 COP")
        
    mfvi = item.get("mfvi_score", 0)
    if mfvi < 70.0:
        violations.append(f"Property {pid}: Low MFVI score: {mfvi}")
        
    wa_link = item.get("whatsapp_url", "")
    if "wa.me/57" not in wa_link:
        violations.append(f"Property {pid}: Missing or invalid WhatsApp link: {wa_link}")
        
    if pid not in dossier_md:
        violations.append(f"Property {pid} missing from DOSSIER_VISITAS.md text")

assert "Puntos" in dossier_md and "Visita" in dossier_md, "Inspection points missing from DOSSIER_VISITAS.md"
assert "Itinerario" in dossier_md, "Visit route/itinerary missing from DOSSIER_VISITAS.md"

print("\n--- R3 AUDIT RESULTS ---")
print(f"Curated count: {len(dossier_items)}")
print(f"Min MFVI score: {min(x['mfvi_score'] for x in dossier_items):.1f}")
print(f"Max MFVI score: {max(x['mfvi_score'] for x in dossier_items):.1f}")
print(f"Price range: ${min(x['total_price'] for x in dossier_items):,} to ${max(x['total_price'] for x in dossier_items):,} COP")
print(f"Neighborhoods: {sorted(list(set(x['neighborhood'] for x in dossier_items)))}")
print(f"Violations count: {len(violations)}")

if violations:
    for v in violations:
        print(f"  VIOLATION: {v}")
    raise SystemExit(1)
else:
    print("ALL R3 ACCEPTANCE CRITERIA VERIFIED 100% CLEAN!")
