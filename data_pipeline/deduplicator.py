"""
data_pipeline/deduplicator.py
Two-tier fuzzy deduplication engine and attribute merging matrix for Barranquilla rental listings.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple

# Canonical mapping for Barranquilla Norte neighborhoods
NEIGHBORHOOD_SYNONYMS: Dict[str, str] = {
    "alto de riomar": "riomar",
    "altos de riomar": "riomar",
    "altos del prado": "alto_prado",
    "alto prado": "alto_prado",
    "el prado": "alto_prado",
    "prado": "alto_prado",
    "la campina": "la_campina",
    "campina": "la_campina",
    "el golf": "el_golf",
    "golf": "el_golf",
    "villa carolina": "villa_carolina",
    "carolina": "villa_carolina",
    "villa santos": "villa_santos",
    "santos": "villa_santos",
    "villa country": "villa_country",
    "country": "villa_country",
    "miramar": "miramar",
    "horizontes de miramar": "miramar",
    "el limoncito": "el_limoncito",
    "limoncito": "el_limoncito",
    "paraiso": "paraiso",
    "bellavista": "bellavista",
    "buenavista": "buenavista",
    "ciudad mallorquin": "ciudad_mallorquin",
    "mallorquin": "ciudad_mallorquin",
    "el tabor": "tabor",
    "tabor": "tabor",
    "los alpes": "los_alpes",
    "alpes": "los_alpes",
    "andalucia": "andalucia",
    "san vicente": "san_vicente",
    "la cumbre": "la_cumbre",
    "cumbre": "la_cumbre",
    "ciudad jardin": "ciudad_jardin",
    "granadillo": "granadillo",
    "golf alto prado": "el_golf",
    "altos de san vicente": "san_vicente",
    "altos del limon": "altos_del_limon",
    "rio alto": "rio_alto",
    "santa monica": "santa_monica",
    "el porvenir": "el_porvenir",
    "porvenir": "el_porvenir",
    "betania": "betania",
    "la concepcion": "la_concepcion",
    "alameda del rio": "alameda_del_rio",
    "villa campestre": "villa_campestre",
    "conjunto residencial villa campestre": "villa_campestre",
    "residencial villa campestre": "villa_campestre"
}

KNOWN_BUILDINGS = [
    "sorrento", "torino", "soho", "mirador", "parque", "alameda",
    "bulevar", "santa barbara", "palmar", "torre 50", "torres de san jose",
    "montecristo", "puerta dorada", "porto verona", "portobelo"
]


def normalize_neighborhood(barrio: Optional[str]) -> str:
    """Normalizes neighborhood name by removing diacritics, noise tokens, and applying canonical synonyms."""
    if not barrio:
        return "desconocido"

    # Strip diacritics
    b = unicodedata.normalize('NFKD', str(barrio)).encode('ASCII', 'ignore').decode('utf-8').lower().strip()
    # Remove noise words
    b = re.sub(r'\b(noroccidente|norte|barranquilla|atlantico|cr\.|urbanizacion|conjunto|sector)\b', '', b)
    # Remove non-alphanumeric characters
    b = re.sub(r'[^a-z0-9]', ' ', b)
    b = ' '.join(b.split())

    if not b:
        return "desconocido"

    return NEIGHBORHOOD_SYNONYMS.get(b, b.replace(' ', '_'))


def compute_canonical_key(
    prop: Dict[str, Any],
    area_bucket_size: int = 5,
    price_bucket_size: int = 100000
) -> str:
    """Generates discrete fingerprint: norm_barrio_bedrooms_hab_bathrooms_ban_areaBkt_priceBkt."""
    norm_barrio = normalize_neighborhood(prop.get("neighborhood", ""))
    bedrooms = max(0, int(prop.get("bedrooms", 0) or 0))
    bathrooms = max(0, int(prop.get("bathrooms", 0) or 0))
    area = float(prop.get("area_m2", 0) or 0)
    price = int(prop.get("total_price", 0) or 0)

    area_bucket = int(round(area / area_bucket_size)) * area_bucket_size if area > 0 else 0
    price_bucket = int(round(price / price_bucket_size)) * price_bucket_size if price > 0 else 0

    return f"{norm_barrio}_{bedrooms}hab_{bathrooms}ban_{area_bucket}m2_{price_bucket}cop"


def calculate_similarity(prop_a: Dict[str, Any], prop_b: Dict[str, Any]) -> float:
    """
    Computes multi-factor similarity score between two listings in [0.0, 1.0].
    Strictly gates on neighborhood, bedrooms, building names, and price/area bounds.
    """
    # 1. Neighborhood check (Hard Gate)
    barrio_a = normalize_neighborhood(prop_a.get("neighborhood", ""))
    barrio_b = normalize_neighborhood(prop_b.get("neighborhood", ""))
    if barrio_a != barrio_b:
        return 0.0

    # 2. Bedrooms check (Hard Gate)
    bed_a = max(0, int(prop_a.get("bedrooms", 0) or 0))
    bed_b = max(0, int(prop_b.get("bedrooms", 0) or 0))
    if bed_a != bed_b:
        return 0.0

    # 3. Bathrooms check (Heavy penalty / rejection if difference >= 2)
    bath_a = int(prop_a.get("bathrooms", 0) or 0)
    bath_b = int(prop_b.get("bathrooms", 0) or 0)
    if bath_a > 0 and bath_b > 0 and abs(bath_a - bath_b) >= 2:
        return 0.0

    # 4. Price Difference (Hard Gate: delta > $150k COP)
    price_a = int(prop_a.get("total_price", 0) or 0)
    price_b = int(prop_b.get("total_price", 0) or 0)
    price_diff = abs(price_a - price_b)
    if price_diff > 150000:
        return 0.0

    # 5. Area Difference
    area_a = float(prop_a.get("area_m2", 0) or 0)
    area_b = float(prop_b.get("area_m2", 0) or 0)
    area_diff = abs(area_a - area_b)

    # Text extraction for building matching and conflict detection
    title_a = str(prop_a.get("title", "")).lower()
    title_b = str(prop_b.get("title", "")).lower()
    addr_a = str(prop_a.get("address", "")).lower()
    addr_b = str(prop_b.get("address", "")).lower()
    desc_a = str(prop_a.get("description", "")).lower()[:150]
    desc_b = str(prop_b.get("description", "")).lower()[:150]
    text_a = f"{title_a} {addr_a} {desc_a}"
    text_b = f"{title_b} {addr_b} {desc_b}"

    # Check for conflicting building names
    buildings_in_a = {b for b in KNOWN_BUILDINGS if b in text_a}
    buildings_in_b = {b for b in KNOWN_BUILDINGS if b in text_b}
    if buildings_in_a and buildings_in_b and not (buildings_in_a & buildings_in_b):
        # Explicitly different buildings
        return 0.0

    token_match = bool(buildings_in_a & buildings_in_b)

    # If area delta is large and no building token match, hard reject
    if area_a > 0 and area_b > 0 and area_diff > 5.0 and not token_match:
        return 0.0

    # Weighted Scoring Matrix:
    # w_barrio = 0.25, w_bed = 0.25, w_bath = 0.15, w_area = 0.15, w_price = 0.20
    score = 0.25 + 0.25  # Barrio and bedrooms match passed hard gates

    # Bathrooms score (weight 0.15)
    if bath_a == bath_b and bath_a > 0:
        score += 0.15
    elif abs(bath_a - bath_b) == 1:
        score += 0.075
    elif bath_a == 0 or bath_b == 0:
        score += 0.075

    # Area score (weight 0.15)
    if area_a > 0 and area_b > 0:
        if area_diff <= 1.0:
            score += 0.15
        elif area_diff <= 3.0:
            score += 0.105
        elif area_diff <= 5.0:
            score += 0.06
    else:
        score += 0.075  # Unspecified area partial score

    # Price score (weight 0.20)
    if price_diff == 0:
        score += 0.20
    elif price_diff <= 50000:
        score += 0.15
    elif price_diff <= 100000:
        score += 0.10
    elif price_diff <= 150000:
        score += 0.05

    # Building / street token bonus (up to 0.10)
    if token_match:
        score += 0.10
    else:
        # Check street numbers like "cra 43", "cra 47", "calle 98"
        for st in ["cra 43", "cra 45", "cra 47", "cra 51", "calle 98", "calle 99", "calle 100"]:
            if st in text_a and st in text_b:
                score += 0.08
                break

    return min(1.0, score)


def clean_id_prefix(listing_id: str) -> str:
    """Strips portal prefixes to extract canonical ID string."""
    return re.sub(r'^(metro_|MQ-|fr_|FR-)', '', str(listing_id))


def merge_cluster(cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merges a cluster of duplicate listings across portals into a single canonical record.
    Prioritizes:
    - Metrocuadrado: unmasked phone & WhatsApp
    - Finca Raíz: high-res photos & detailed specs
    - Explicit administration fee
    - Tenant-optimal total price <= 2.5M COP
    """
    if len(cluster) == 1:
        return cluster[0]

    metro_props = [p for p in cluster if "metro" in p.get("portal", "").lower()]
    finca_props = [p for p in cluster if "finca" in p.get("portal", "").lower()]

    primary = metro_props[0] if metro_props else cluster[0]
    secondary = finca_props[0] if finca_props else cluster[-1]

    # 1. ID and Portal
    is_cross = len(metro_props) > 0 and len(finca_props) > 0
    all_ids = [p["id"] for p in cluster]

    if is_cross:
        id_a = clean_id_prefix(primary["id"])
        id_b = clean_id_prefix(secondary["id"])
        merged_id = f"MERGED-{id_a}-{id_b}"
        portal_name = "Metrocuadrado + Finca Raiz"
    else:
        merged_id = primary["id"]
        portal_name = primary["portal"]

    # 2. Contact merging (Unmasked phone & WhatsApp prioritized from Metrocuadrado)
    phone = ""
    whatsapp = ""
    agency = ""
    agent_name = ""

    for p in cluster:
        c = p.get("contact") or {}
        raw_ph = str(c.get("phone") or p.get("contact_phone") or "").strip()
        clean_digits = re.sub(r'\D', '', raw_ph)
        if len(clean_digits) >= 7 and not raw_ph.startswith("+5730") and not raw_ph.endswith("*"):
            phone = raw_ph
            break

    if not phone and primary.get("contact", {}).get("phone"):
        phone = primary["contact"]["phone"]

    for p in cluster:
        c = p.get("contact") or {}
        raw_wa = str(c.get("whatsapp") or p.get("whatsapp") or "").strip()
        clean_wa = re.sub(r'\D', '', raw_wa)
        if len(clean_wa) >= 10:
            whatsapp = raw_wa
            break

    if not whatsapp and phone and len(re.sub(r'\D', '', phone)) == 10 and re.sub(r'\D', '', phone).startswith("3"):
        whatsapp = "57" + re.sub(r'\D', '', phone)

    agencies: Set[str] = set()
    for p in cluster:
        c = p.get("contact") or {}
        ag = c.get("agency") or p.get("agency")
        if ag and isinstance(ag, str) and len(ag.strip()) > 2:
            agencies.add(ag.strip())
        ag_n = c.get("agent_name") or p.get("agent_name")
        if ag_n and isinstance(ag_n, str) and not agent_name and ag_n != ag:
            agent_name = ag_n.strip()

    agency = " / ".join(sorted(agencies)) if agencies else primary.get("contact", {}).get("agency", "Inmobiliaria")
    if not agent_name:
        agent_name = primary.get("contact", {}).get("agent_name", "Asesor Comercial")

    # 3. Financials (Explicit admin fee preferred, tenant-optimal total price)
    explicit_admin_props = [p for p in cluster if int(p.get("admin_fee", 0) or 0) > 0]
    min_total = min(int(p["total_price"]) for p in cluster)

    if explicit_admin_props:
        admin_fee = int(explicit_admin_props[0]["admin_fee"])
        total_price = min_total
        canon = total_price - admin_fee if total_price >= admin_fee else total_price
    else:
        total_price = min_total
        admin_fee = 0
        canon = total_price

    # 4. Images (Union of all unique image URLs, preserving order)
    seen_urls: Set[str] = set()
    combined_images: List[str] = []
    for p in cluster:
        for img in p.get("images", []):
            if img and isinstance(img, str) and img.startswith("http"):
                clean_img = img.split("?")[0]
                if clean_img not in seen_urls:
                    seen_urls.add(clean_img)
                    combined_images.append(img)

    # 5. Physical attributes (Take max / most complete)
    area_m2 = max(float(p.get("area_m2", 0) or 0) for p in cluster)
    bedrooms = max(max(0, int(p.get("bedrooms", 0) or 0)) for p in cluster)
    bathrooms = max(int(p.get("bathrooms", 0) or 0) for p in cluster)
    parking = max(int(p.get("parking", 0) or 0) for p in cluster)

    valid_strata = [
        int(p["stratum"])
        for p in cluster
        if p.get("stratum") is not None and 1 <= int(p["stratum"]) <= 6
    ]
    stratum = max(valid_strata) if valid_strata else None

    # 6. Title, Address, Description
    titles = [p.get("title", "") for p in cluster if p.get("title")]
    titles.sort(key=lambda t: (not t.isupper(), len(t)), reverse=True)
    title = titles[0] if titles else "Apartamento en Arriendo"

    addresses = [p.get("address", "") for p in cluster if p.get("address")]
    addresses.sort(key=len, reverse=True)
    address = addresses[0] if addresses else primary.get("neighborhood", "")

    descriptions = [p.get("description", "") for p in cluster if p.get("description")]
    descriptions.sort(key=len, reverse=True)
    description = descriptions[0] if descriptions else ""

    # 7. URL (Prefer Metrocuadrado for direct contact, or Finca Raiz)
    chosen_url = primary.get("url") or secondary.get("url", "")
    source_urls = [{"portal": p.get("portal", "unknown"), "url": p.get("url", "")} for p in cluster]

    prop_type = "Casa" if any("casa" in str(p.get("property_type", "")).lower() for p in cluster) else "Apartamento"

    # Strict zone contract conformance ('Norte' | 'Noroccidente')
    clean_zone = primary.get("zone", "")
    norm_barrio = normalize_neighborhood(primary.get("neighborhood", ""))
    if "mallorquin" in norm_barrio:
        resolved_zone = "Noroccidente"
    elif clean_zone in ("Norte", "Noroccidente"):
        resolved_zone = clean_zone
    else:
        cluster_zones = [p.get("zone") for p in cluster if p.get("zone") in ("Norte", "Noroccidente")]
        if cluster_zones:
            resolved_zone = cluster_zones[0]
        else:
            resolved_zone = "Noroccidente" if "noroccidente" in str(clean_zone).lower() else "Norte"

    return {
        "id": merged_id,
        "portal": portal_name,
        "title": title,
        "property_type": prop_type,
        "canon": canon,
        "admin_fee": admin_fee,
        "total_price": total_price,
        "neighborhood": primary.get("neighborhood", "Barranquilla"),
        "zone": resolved_zone,
        "address": address,
        "area_m2": area_m2,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "parking": parking,
        "stratum": stratum,
        "images": combined_images,
        "url": chosen_url,
        "contact": {
            "phone": phone,
            "whatsapp": whatsapp,
            "agency": agency,
            "agent_name": agent_name
        },
        "description": description,
        "verified": any(p.get("verified", False) for p in cluster),
        "source_urls": source_urls,
        "source_ids": all_ids
    }


def deduplicate_listings(
    listings: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Two-tier fuzzy deduplication engine:
    - Tier 1: Exact key hash blocking by (norm_barrio, bedrooms)
    - Tier 2: Multi-factor similarity scoring S(A, B) >= 0.70
    - Union-Find cluster consolidation
    - Attribute merging matrix
    """
    if not listings:
        return [], {"input": 0, "output": 0, "merged_duplicates": 0, "clusters_formed": 0}

    n = len(listings)
    parent = list(range(n))

    def find(i: int) -> int:
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i: int, j: int) -> None:
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_j] = root_i

    # Blocking by (norm_barrio, bedrooms)
    blocks: Dict[Tuple[str, int], List[int]] = {}
    for idx, prop in enumerate(listings):
        barrio = normalize_neighborhood(prop.get("neighborhood", ""))
        beds = max(0, int(prop.get("bedrooms", 0) or 0))
        key = (barrio, beds)
        blocks.setdefault(key, []).append(idx)

    # Pairwise comparison within candidate blocks
    for _, indices in blocks.items():
        m = len(indices)
        for i in range(m):
            for j in range(i + 1, m):
                idx_a, idx_b = indices[i], indices[j]
                prop_a, prop_b = listings[idx_a], listings[idx_b]
                sim = calculate_similarity(prop_a, prop_b)
                if sim >= 0.70:
                    union(idx_a, idx_b)

    # Group into clusters
    clusters: Dict[int, List[Dict[str, Any]]] = {}
    for idx in range(n):
        root = find(idx)
        clusters.setdefault(root, []).append(listings[idx])

    # Merge each cluster
    deduped: List[Dict[str, Any]] = []
    merged_count = 0
    for _, prop_list in clusters.items():
        if len(prop_list) > 1:
            merged_count += (len(prop_list) - 1)
        deduped.append(merge_cluster(prop_list))

    stats = {
        "input": n,
        "output": len(deduped),
        "merged_duplicates": merged_count,
        "clusters_formed": len(clusters)
    }

    return deduped, stats
