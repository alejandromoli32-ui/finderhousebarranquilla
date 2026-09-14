import sys
sys.path.insert(0, '.')
import json
import re
from data_pipeline.deduplicator import deduplicate_listings, normalize_neighborhood

# Load fallback data
with open('data_pipeline/fallback_data.json', encoding='utf-8') as f:
    raw = json.load(f)

# Extended ALLOWED_BARRIOS
ALLOWED_BARRIOS = {
    "el_golf", "alto_prado", "riomar", "villa_santos", "villa_country",
    "miramar", "villa_carolina", "el_limoncito", "paraiso", "bellavista",
    "buenavista", "ciudad_mallorquin", "la_campina", "tabor", "los_alpes",
    "andalucia", "san_vicente", "la_cumbre", "ciudad_jardin", "granadillo",
    "el_porvenir", "betania", "rio_alto", "alameda_del_rio", "santa_monica",
    "la_concepcion", "villa_campestre",
    "desconocido"
}

SYNONYMS = {
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

DISALLOWED_MUNICIPALITIES = {
    "puerto_colombia", "puerto colombia", "soledad", "malambo", "galapa",
    "baranoa", "sabanagrande", "palmar_de_varela", "tubara", "juan_de_acosta"
}

DISALLOWED_TOKENS = [
    r"\bpuerto colombia\b", r"\bpuerto_colombia\b", r"\bpuerto-colombia\b",
    r"\bsoledad\b", r"\bmalambo\b", r"\bgalapa\b", r"\bbaranoa\b", r"\bsabanagrande\b",
    r"\brebolo\b", r"\bchinita\b", r"\bla chinita\b", r"\bel bosque\b",
    r"\bsimon bolivar\b", r"\bsimón bolívar\b", r"\bsan roque\b",
    r"\bchiquinquira\b", r"\bchiquinquirá\b", r"\bmontes\b", r"\blos montes\b",
    r"\bsuroriente\b", r"\bsuroccidente\b"
]

def clean_barrio(barrio):
    norm = normalize_neighborhood(barrio)
    raw_lower = str(barrio or '').lower().strip()
    for k, v in SYNONYMS.items():
        if k in raw_lower or k in norm:
            return v
    return norm

def validate_and_sanitize(prop):
    if not isinstance(prop, dict) or not prop.get("id") or not prop.get("title"):
        return False, "Missing id or title"

    # Price validation
    try:
        canon = int(prop.get("canon", 0) or 0)
        admin_fee = int(prop.get("admin_fee", 0) or 0)
    except (ValueError, TypeError):
        return False, "Price fields must be numeric integers"

    if canon <= 0 or admin_fee < 0:
        return False, "Invalid canon or admin"
    total_price = canon + admin_fee
    if total_price > 2500000:
        return False, "Exceeds budget ceiling"
    prop["canon"] = canon
    prop["admin_fee"] = admin_fee
    prop["total_price"] = total_price

    # Geography validation
    barrio = prop.get("neighborhood", "")
    norm_barrio = clean_barrio(barrio)
    zone = str(prop.get("zone", "")).lower()
    title = str(prop.get("title", "")).lower()
    address = str(prop.get("address", "")).lower()
    url = str(prop.get("url", "")).lower()
    geo_text = f"{barrio} {title} {address} {url}".lower()

    # Municipality Gate
    is_mallorquin = ("mallorquin" in norm_barrio) or ("mallorquin" in title) or ("mallorquin" in address)
    if norm_barrio in DISALLOWED_MUNICIPALITIES:
        return False, f"External municipality: {norm_barrio}"
    for pat in DISALLOWED_TOKENS:
        if re.search(pat, geo_text):
            if "puerto" in pat and is_mallorquin:
                continue
            return False, f"Matched disallowed token: {pat}"

    # Target Sector Gate
    is_allowed = norm_barrio in ALLOWED_BARRIOS
    is_norte_zone = any(z in zone for z in ["norte", "noroccidente", "riomar", "historico"])
    if is_allowed and norm_barrio != "desconocido":
        pass
    elif norm_barrio == "desconocido" and is_norte_zone:
        pass
    else:
        return False, f"Neighborhood '{barrio}' not in target sector"

    # URL check
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, "Invalid URL"

    # Sanitization
    try:
        raw_beds = int(prop.get("bedrooms", 1) or 1)
        prop["bedrooms"] = max(1, raw_beds)
    except (ValueError, TypeError):
        prop["bedrooms"] = 1

    try:
        raw_stratum = int(prop.get("stratum", 4) or 4)
        prop["stratum"] = raw_stratum if 1 <= raw_stratum <= 6 else 4
    except (ValueError, TypeError):
        prop["stratum"] = 4

    clean_zone = str(prop.get("zone", "Norte")).strip()
    if clean_zone not in ["Norte", "Noroccidente"]:
        if "noroccidente" in clean_zone.lower() or norm_barrio in ["miramar", "ciudad_mallorquin"]:
            prop["zone"] = "Noroccidente"
        else:
            prop["zone"] = "Norte"
    else:
        prop["zone"] = clean_zone

    return True, "Valid"

passed = []
for p in raw:
    ok, _ = validate_and_sanitize(p)
    if ok:
        passed.append(p)

deduped, stats = deduplicate_listings(passed)

# In deduplicator line 334 fix:
for p in deduped:
    if p["zone"] not in ["Norte", "Noroccidente"]:
        p["zone"] = "Noroccidente" if "noroccidente" in p["zone"].lower() else "Norte"

print(f"Raw count: {len(raw)}, Valid: {len(passed)}, Deduped: {len(deduped)}, Merged: {stats['merged_duplicates']}")

# Now verify the adversarial conditions
leaks = [p for p in deduped if str(p.get("neighborhood","")).strip().lower() == "puerto colombia" or "puerto-colombia" in str(p.get("url","")).lower()]
print(f"Puerto Colombia leaks in deduped: {len(leaks)}")

bad_beds = [p for p in deduped if p.get("bedrooms") is None or p.get("bedrooms") < 1]
print(f"Bad bedrooms in deduped: {len(bad_beds)}")

bad_stratum = [p for p in deduped if p.get("stratum") not in range(1, 7)]
print(f"Bad stratum in deduped: {len(bad_stratum)}")

bad_zone = [p for p in deduped if p.get("zone") not in ["Norte", "Noroccidente"]]
print(f"Bad zone in deduped: {len(bad_zone)}")
