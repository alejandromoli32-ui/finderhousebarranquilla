import json

with open(".agents/explorer_m1_1/metrocuadrado_sample_dataset.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Loaded {len(data)} properties.")

# Schema check
required_keys = [
    "id", "portal", "title", "property_type", "canon", "admin_fee", "total_price",
    "neighborhood", "zone", "address", "area_m2", "bedrooms", "bathrooms",
    "parking", "stratum", "images", "url", "contact", "description", "verified"
]

contact_keys = ["phone", "whatsapp", "agency", "agent_name"]

errors = []
barrio_counts = {}
for idx, p in enumerate(data):
    for k in required_keys:
        if k not in p:
            errors.append(f"Item {idx} missing key: {k}")
    if "contact" in p:
        for ck in contact_keys:
            if ck not in p["contact"]:
                errors.append(f"Item {idx} contact missing key: {ck}")
    
    # Financial integrity
    if p.get("total_price") > 2500000:
        errors.append(f"Item {idx} ({p.get('id')}) exceeds 2.5M: {p.get('total_price')}")
    if p.get("total_price") != (p.get("canon") + p.get("admin_fee")):
        errors.append(f"Item {idx} math mismatch: total {p.get('total_price')} != canon {p.get('canon')} + admin {p.get('admin_fee')}")
        
    b = p.get("neighborhood")
    barrio_counts[b] = barrio_counts.get(b, 0) + 1

print(f"Schema validation errors: {len(errors)}")
if errors:
    for e in errors[:10]:
        print("  ", e)

print("\nProperties by Neighborhood:")
for b, c in sorted(barrio_counts.items(), key=lambda x: -x[1]):
    print(f"  {b:25}: {c} properties")

has_wa = sum(1 for p in data if p["contact"]["whatsapp"])
has_phone = sum(1 for p in data if p["contact"]["phone"])
has_images = sum(1 for p in data if len(p["images"]) > 0)
print(f"\nWhatsApp availability: {has_wa}/{len(data)} ({has_wa/len(data)*100:.1f}%)")
print(f"Phone availability: {has_phone}/{len(data)} ({has_phone/len(data)*100:.1f}%)")
print(f"Images availability: {has_images}/{len(data)} ({has_images/len(data)*100:.1f}%)")
