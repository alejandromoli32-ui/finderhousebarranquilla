import json

with open("data/inmuebles_barranquilla.json", "r", encoding="utf-8") as f:
    data = json.load(f)

merged_props = [p for p in data if len(p.get("source_ids", [])) > 1 or "MERGED" in p.get("id", "")]
print(f"Total merged properties in final database: {len(merged_props)}")

suspect_merges = []
for p in merged_props:
    s_urls = p.get("source_urls", [])
    # Check if addresses or titles differ wildly
    title = p.get("title", "")
    address = p.get("address", "")
    p_id = p.get("id", "")
    sources = [s.get("portal") for s in s_urls]
    print(f"ID: {p_id} | Barrio: {p.get('neighborhood')} | Beds: {p.get('bedrooms')} | Baths: {p.get('bathrooms')} | Area: {p.get('area_m2')} | Total: {p.get('total_price')} | Portals: {sources} | Title: {title[:40]} | Addr: {address[:40]}")
