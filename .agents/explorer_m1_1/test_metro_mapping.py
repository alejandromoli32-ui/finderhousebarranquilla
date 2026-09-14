import urllib.request
import ssl
import json
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/x-component",
    "RSC": "1",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def clean_neighborhood_name(name):
    if not name:
        return "Norte"
    name = name.strip()
    words = name.split()
    # Title-case each word except small prepositions
    clean_words = []
    for i, w in enumerate(words):
        w_lower = w.lower()
        if w_lower in ["de", "del", "la", "el", "los", "las", "y"] and i > 0:
            clean_words.append(w_lower)
        else:
            clean_words.append(w_lower.capitalize())
    return " ".join(clean_words)

def normalize_whatsapp(phone, wa_raw):
    raw = wa_raw or phone or ""
    # Strip non-digits
    digits = re.sub(r'\D', '', str(raw))
    if not digits:
        return ""
    # If 10 digits starting with 3, prefix with 57
    if len(digits) == 10 and digits.startswith("3"):
        return "57" + digits
    # If 12 digits starting with 573
    if len(digits) == 12 and digits.startswith("573"):
        return digits
    return digits

def map_metro_item(itm, default_barrio=None):
    mid = str(itm.get("midinmueble", "")).strip()
    if not mid:
        return None
    
    # Financials
    try:
        canon = int(round(float(itm.get("mvalorarriendo") or 0)))
    except:
        canon = 0
        
    admin_fee = 0
    try:
        admin_raw = itm.get("data", {}).get("mvaloradministracion")
        if admin_raw is not None:
            admin_fee = int(round(float(admin_raw)))
    except:
        admin_fee = 0
        
    total_price = canon + admin_fee
    # Price ceiling rule
    if total_price <= 0 or total_price > 2500000:
        return None
        
    # Neighborhood & Zone
    barrio_raw = itm.get("mnombrecomunbarrio") or itm.get("mbarrio") or default_barrio or "Norte"
    neighborhood = clean_neighborhood_name(barrio_raw)
    
    # Property type
    ptype_raw = itm.get("mtipoinmueble", {}).get("nombre", "Apartamento")
    if "casa" in ptype_raw.lower():
        property_type = "Casa"
    else:
        property_type = "Apartamento"
        
    # Physical specs
    try:
        area_m2 = float(itm.get("marea") or itm.get("mareac") or 0)
    except:
        area_m2 = 0.0
        
    try:
        bedrooms = int(itm.get("mnrocuartos") or 1)
    except:
        bedrooms = 1
        
    try:
        bathrooms = int(itm.get("mnrobanos") or 1)
    except:
        bathrooms = 1
        
    try:
        parking = int(itm.get("mnrogarajes") or 0)
    except:
        parking = 0
        
    try:
        stratum = int(itm.get("estrato") or 4)
    except:
        stratum = 4
        
    # Title
    title = itm.get("title") or f"{property_type} en Arriendo en {neighborhood}, Barranquilla"
    
    # URL
    link = itm.get("link") or itm.get("data", {}).get("murldetalle") or ""
    if link.startswith("/"):
        url = f"https://www.metrocuadrado.com{link}"
    else:
        url = link or f"https://www.metrocuadrado.com/inmueble/{mid}"
        
    # Images
    images = []
    main_img = itm.get("imageLink")
    if main_img:
        # Also provide high-res version without _p
        high_res = main_img.replace("_p.jpg", ".jpg")
        images.append(high_res)
    
    gallery = itm.get("mgaleriainmueble") or []
    for g_id in gallery[:10]:
        g_url = f"https://multimedia.metrocuadrado.com/{mid}/{g_id}.jpg"
        if g_url not in images:
            images.append(g_url)
            
    if not images and main_img:
        images.append(main_img)
        
    # Contact
    phone = str(itm.get("contactPhone") or "").strip()
    wa_raw = str(itm.get("whatsapp") or "").strip()
    whatsapp = normalize_whatsapp(phone, wa_raw)
    
    visitor = itm.get("data", {}).get("mnombrevisitor") or ""
    owner_type = itm.get("OwnerType") or "Inmobiliaria"
    agency = visitor if "s.a" in visitor.lower() or "inmobiliaria" in visitor.lower() or "sas" in visitor.lower() or "ltda" in visitor.lower() else owner_type
    agent_name = visitor if visitor else "Asesor Comercial"
    
    # Address
    address = itm.get("mnombreproyecto") or f"{neighborhood}, Barranquilla"
    
    # Zone
    zona_obj = itm.get("mzona") or {}
    zone_name = zona_obj.get("nombre") if isinstance(zona_obj, dict) else None
    if not zone_name:
        zone_name = "Noroccidente" if any(nb in neighborhood.lower() for nb in ["miramar", "riomar", "santos", "mallorquin"]) else "Norte"

    # Description
    desc = itm.get("comment") or itm.get("whatsappMessage") or ""
    
    return {
        "id": f"MQ-{mid}",
        "portal": "Metrocuadrado",
        "title": title,
        "property_type": property_type,
        "canon": canon,
        "admin_fee": admin_fee,
        "total_price": total_price,
        "neighborhood": neighborhood,
        "zone": zone_name,
        "address": address,
        "area_m2": area_m2,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "parking": parking,
        "stratum": stratum,
        "images": images,
        "url": url,
        "contact": {
            "phone": phone,
            "whatsapp": whatsapp,
            "agency": agency,
            "agent_name": agent_name
        },
        "description": desc,
        "verified": True
    }

# Test with Miramar
url = "https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/miramar/"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    body = resp.read().decode('utf-8', errors='ignore')

# parse RSC
start_pos = body.find('"initialResults":{')
obj_start = start_pos + len('"initialResults":')
cnt = 0
for i in range(obj_start, len(body)):
    if body[i] == '{': cnt += 1
    elif body[i] == '}':
        cnt -= 1
        if cnt == 0:
            obj_end = i + 1
            break
data = json.loads(body[obj_start:obj_end])
results = data.get("results", [])

normalized = []
for itm in results:
    m = map_metro_item(itm, default_barrio="Miramar")
    if m:
        normalized.append(m)

print(f"Total Miramar raw: {len(results)}, successfully normalized under $2.5M: {len(normalized)}")
if normalized:
    print("\n--- Sample Normalized Record ---")
    print(json.dumps(normalized[0], indent=2, ensure_ascii=False))
