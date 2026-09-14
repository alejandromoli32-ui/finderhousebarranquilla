import json
import csv
from pathlib import Path
from urllib.parse import urlparse

json_path = Path("data/inmuebles_barranquilla.json")
csv_path = Path("data/inmuebles_barranquilla.csv")

assert json_path.exists(), "data/inmuebles_barranquilla.json does not exist"
assert csv_path.exists(), "data/inmuebles_barranquilla.csv does not exist"

with open(json_path, encoding="utf-8") as f:
    listings = json.load(f)

print(f"Total listings in JSON: {len(listings)}")

# Check CSV consistency
with open(csv_path, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    csv_rows = list(reader)
print(f"Total listings in CSV: {len(csv_rows)}")
assert len(listings) == len(csv_rows), f"Mismatch count JSON ({len(listings)}) vs CSV ({len(csv_rows)})"

# Required fields per ORIGINAL_REQUEST.md
required_fields = [
    "id", "title", "property_type", "canon", "admin_fee", "total_price",
    "neighborhood", "area_m2", "bedrooms", "bathrooms", "parking",
    "images", "url", "contact"
]

budget_ceiling = 2500000
violations = []
ids = set()
urls = set()
neighborhoods = set()
property_types = set()
portals = set()

for i, item in enumerate(listings):
    # 1. Check required fields
    for field in required_fields:
        if field not in item:
            violations.append(f"Listing #{i} ({item.get('id')}): missing required field '{field}'")
    
    # 2. Check unique ID and URL
    lid = item.get("id")
    if lid in ids:
        violations.append(f"Duplicate ID found: {lid}")
    ids.add(lid)
    
    url = item.get("url", "")
    if not (url.startswith("http://") or url.startswith("https://")):
        violations.append(f"Listing {lid}: Invalid URL '{url}'")
    if url in urls:
        violations.append(f"Duplicate URL found: {url}")
    urls.add(url)
    
    domain = urlparse(url).netloc.lower()
    portals.add(domain)

    # 3. Check price invariants
    canon = item.get("canon", 0)
    admin = item.get("admin_fee", 0)
    total = item.get("total_price", 0)
    
    if total > budget_ceiling:
        violations.append(f"Listing {lid}: Total price ${total} exceeds budget ceiling ${budget_ceiling}")
    
    if canon + admin != total:
        violations.append(f"Listing {lid}: Math mismatch: canon({canon}) + admin({admin}) = {canon+admin} != total({total})")
    
    # 4. Check contact info
    contact = item.get("contact", {})
    if not isinstance(contact, dict) or not contact.get("phone"):
        violations.append(f"Listing {lid}: Missing or invalid contact phone")
    
    # 5. Check images
    images = item.get("images", [])
    if not isinstance(images, list) or len(images) == 0:
        violations.append(f"Listing {lid}: Missing images list")
        
    # 6. Physical features
    area = item.get("area_m2", 0)
    beds = item.get("bedrooms", 0)
    baths = item.get("bathrooms", 0)
    if area <= 0 or beds < 0 or baths < 0:
        violations.append(f"Listing {lid}: Unrealistic physical attributes: area={area}, beds={beds}, baths={baths}")
        
    neighborhoods.add(item.get("neighborhood"))
    property_types.add(item.get("property_type"))

print("\n--- R1 AUDIT RESULTS ---")
print(f"Portals represented: {portals}")
print(f"Property types: {property_types}")
print(f"Distinct neighborhoods: {len(neighborhoods)}")
print(f"Neighborhoods sample: {sorted(list(neighborhoods))[:15]}")
print(f"Min total price: ${min(x['total_price'] for x in listings):,}")
print(f"Max total price: ${max(x['total_price'] for x in listings):,}")
print(f"Violations count: {len(violations)}")

if violations:
    for v in violations[:10]:
        print(f"  VIOLATION: {v}")
    raise SystemExit(1)
else:
    print("ALL R1 ACCEPTANCE CRITERIA VERIFIED 100% CLEAN!")
