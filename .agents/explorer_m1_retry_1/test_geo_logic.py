import sys
sys.path.insert(0, '.')
import json
import re
from data_pipeline.deduplicator import deduplicate_listings, normalize_neighborhood

with open('data_pipeline/fallback_data.json', encoding='utf-8') as f:
    raw = json.load(f)

# Extended ALLOWED_BARRIOS including northern aledaños
EXTENDED_ALLOWED_BARRIOS = {
    "el_golf", "alto_prado", "riomar", "villa_santos", "villa_country",
    "miramar", "villa_carolina", "el_limoncito", "paraiso", "bellavista",
    "buenavista", "ciudad_mallorquin", "la_campina", "tabor", "los_alpes",
    "andalucia", "san_vicente", "la_cumbre", "ciudad_jardin", "granadillo",
    "el_porvenir", "betania", "rio_alto", "alameda_del_rio", "santa_monica",
    "la_concepcion", "villa_campestre",
    "desconocido"
}

# Extended synonyms
EXTENDED_SYNONYMS = {
    "ciudad de mallorquin": "ciudad_mallorquin",
    "ciudad mallorquin zona urbana": "ciudad_mallorquin",
    "golf alto prado": "el_golf",
    "el paraiso": "paraiso",
    "villa paraiso": "paraiso",
    "altos de san vicente": "san_vicente",
    "altos del limon": "el_limoncito",
    "conjunto residencial villa campestre": "villa_campestre",
    "residencial villa campestre": "villa_campestre"
}

def clean_barrio(barrio):
    norm = normalize_neighborhood(barrio)
    raw_lower = str(barrio or '').lower().strip()
    # Check synonyms
    for k, v in EXTENDED_SYNONYMS.items():
        if k in raw_lower or k in norm:
            return v
    return norm

# Disallowed tokens for non-Barranquilla / excluded sectors
DISALLOWED_MUNI_TOKENS = [
    r"\bpuerto colombia\b", r"\bpuerto_colombia\b", r"\bpuerto-colombia\b",
    r"\bsoledad\b", r"\bmalambo\b", r"\bgalapa\b", r"\bbaranoa\b", r"\bsabanagrande\b",
    r"\brebolo\b", r"\bchinita\b", r"\bel bosque\b", r"\bsimon bolivar\b",
    r"\bsan roque\b", r"\bchiquinquira\b", r"\bmontes\b", r"\bsuroriente\b",
    r"\bsuroccidente\b", r"\babajo\b"
]

def validate_geo(prop):
    barrio = prop.get("neighborhood", "")
    norm_barrio = clean_barrio(barrio)
    zone = str(prop.get("zone", "")).lower()
    title = str(prop.get("title", "")).lower()
    address = str(prop.get("address", "")).lower()
    url = str(prop.get("url", "")).lower()
    text_geo = f"{barrio} {title} {address} {url}".lower()

    # Step 1: Municipality & Disallowed Sectors Hard Gate (Conjunction Premise 1)
    # Special exemption: Ciudad Mallorquín is permitted as a border sector even if Puerto Colombia is referenced in portal metadata
    is_mallorquin = ("mallorquin" in norm_barrio) or ("mallorquin" in title)
    
    for pat in DISALLOWED_MUNI_TOKENS:
        if re.search(pat, text_geo):
            # If the match is "puerto colombia" or "puerto-colombia", allow ONLY if it is specifically Ciudad Mallorquín
            if "puerto" in pat and is_mallorquin:
                continue
            return False, f"Listing matched disallowed municipality or excluded sector: {pat}"

    # Step 2: Target Sector Whitelist & Zone Conjunction (Conjunction Premise 2)
    is_allowed = norm_barrio in EXTENDED_ALLOWED_BARRIOS
    is_norte_zone = any(z in zone for z in ["norte", "noroccidente", "riomar", "historico"])

    if not is_allowed:
        if norm_barrio == "desconocido" and is_norte_zone:
            pass
        else:
            return False, f"Neighborhood '{barrio}' ({norm_barrio}) not in target sector whitelist"
            
    return True, "Valid"

passed = []
rejected = []
for p in raw:
    ok, reason = validate_geo(p)
    if ok:
        passed.append(p)
    else:
        rejected.append((p['id'], p.get('neighborhood'), reason))

print(f"Total raw: {len(raw)}")
print(f"Passed: {len(passed)}, Rejected: {len(rejected)}")
for r in rejected:
    print("REJECTED:", r)

deduped, stats = deduplicate_listings(passed)
print(f"Deduped count: {len(deduped)}, Merged: {stats['merged_duplicates']}")
