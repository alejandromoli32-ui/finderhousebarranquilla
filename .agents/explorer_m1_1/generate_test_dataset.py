import urllib.request
import ssl
import json
import re
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/x-component",
    "RSC": "1",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

neighborhood_slugs = [
    ("miramar", "Miramar", "Noroccidente"),
    ("villa-carolina", "Villa Carolina", "Norte"),
    ("villa-country", "Villa Country", "Norte"),
    ("alto-prado", "Alto Prado", "Norte"),
    ("villa-santos", "Villa Santos", "Noroccidente"),
    ("riomar", "Riomar", "Noroccidente"),
    ("el-golf", "El Golf", "Norte"),
    ("ciudad-mallorquin", "Ciudad Mallorquin", "Noroccidente"),
    ("altos-de-riomar", "Altos de Riomar", "Noroccidente"),
    ("buenavista", "Buenavista", "Noroccidente"),
    ("paraiso", "Paraiso", "Norte"),
    ("bellavista", "Bellavista", "Norte"),
    ("el-prado", "El Prado", "Norte"),
    ("el-limoncito", "El Limoncito", "Norte"),
    ("tabor", "El Tabor", "Noroccidente"),
    ("los-alpes", "Los Alpes", "Noroccidente"),
    ("andalucia", "Andalucia", "Noroccidente"),
    ("san-vicente", "San Vicente", "Norte"),
    ("la-campina", "La Campina", "Noroccidente"),
    ("la-cumbre", "La Cumbre", "Noroccidente")
]

def clean_neighborhood_name(name):
    if not name: return "Norte"
    name = name.strip()
    words = name.split()
    clean = []
    for i, w in enumerate(words):
        wl = w.lower()
        if wl in ["de", "del", "la", "el", "los", "las", "y"] and i > 0:
            clean.append(wl)
        else:
            clean.append(wl.capitalize())
    return " ".join(clean)

def normalize_whatsapp(phone, wa_raw):
    raw = wa_raw or phone or ""
    digits = re.sub(r'\D', '', str(raw))
    if len(digits) == 10 and digits.startswith("3"):
        return "57" + digits
    if len(digits) == 12 and digits.startswith("573"):
        return digits
    return digits

def map_metro_item(itm, default_barrio, default_zone):
    mid = str(itm.get("midinmueble", "")).strip()
    if not mid: return None
    
    try: canon = int(round(float(itm.get("mvalorarriendo") or 0)))
    except: canon = 0
    
    admin_fee = 0
    try:
        raw_admin = itm.get("data", {}).get("mvaloradministracion")
        if raw_admin is not None:
            admin_fee = int(round(float(raw_admin)))
    except:
        admin_fee = 0
        
    total_price = canon + admin_fee
    if total_price <= 0 or total_price > 2500000:
        return None
        
    barrio_raw = itm.get("mnombrecomunbarrio") or itm.get("mbarrio") or default_barrio
    neighborhood = clean_neighborhood_name(barrio_raw)
    
    ptype_raw = itm.get("mtipoinmueble", {}).get("nombre", "Apartamento")
    property_type = "Casa" if "casa" in ptype_raw.lower() else "Apartamento"
    
    try: area_m2 = float(itm.get("marea") or itm.get("mareac") or 0)
    except: area_m2 = 0.0
    
    try: bedrooms = int(itm.get("mnrocuartos") or 1)
    except: bedrooms = 1
    
    try: bathrooms = int(itm.get("mnrobanos") or 1)
    except: bathrooms = 1
    
    try: parking = int(itm.get("mnrogarajes") or 0)
    except: parking = 0
    
    try: stratum = int(itm.get("estrato") or 4)
    except: stratum = 4
    
    title = itm.get("title") or f"{property_type} en Arriendo en {neighborhood}, Barranquilla"
    
    link = itm.get("link") or itm.get("data", {}).get("murldetalle") or ""
    url = f"https://www.metrocuadrado.com{link}" if link.startswith("/") else (link or f"https://www.metrocuadrado.com/inmueble/{mid}")
    
    images = []
    main_img = itm.get("imageLink")
    if main_img:
        images.append(main_img.replace("_p.jpg", ".jpg"))
        
    gallery = itm.get("mgaleriainmueble") or []
    for gid in gallery[:10]:
        gurl = f"https://multimedia.metrocuadrado.com/{mid}/{gid}.jpg"
        if gurl not in images:
            images.append(gurl)
            
    if not images and main_img:
        images.append(main_img)
        
    phone = str(itm.get("contactPhone") or "").strip()
    wa_raw = str(itm.get("whatsapp") or "").strip()
    whatsapp = normalize_whatsapp(phone, wa_raw)
    
    visitor = itm.get("data", {}).get("mnombrevisitor") or ""
    owner_type = itm.get("OwnerType") or "Inmobiliaria"
    agency = visitor if any(k in visitor.lower() for k in ["s.a", "inmobiliaria", "sas", "ltda"]) else owner_type
    agent_name = visitor if visitor else "Asesor Comercial"
    
    address = itm.get("mnombreproyecto") or f"{neighborhood}, Barranquilla"
    
    zona_obj = itm.get("mzona") or {}
    zone_name = zona_obj.get("nombre") if isinstance(zona_obj, dict) else None
    if not zone_name:
        zone_name = default_zone
        
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

def parse_rsc(body):
    start = body.find('"initialResults":{')
    if start == -1:
        res_pos = body.find('"results":[')
        if res_pos == -1: return []
        arr_start = res_pos + len('"results":')
        cnt = 0
        for i in range(arr_start, len(body)):
            if body[i] == '[': cnt += 1
            elif body[i] == ']':
                cnt -= 1
                if cnt == 0:
                    try: return json.loads(body[arr_start:i+1])
                    except: return []
        return []
    
    obj_start = start + len('"initialResults":')
    cnt = 0
    for i in range(obj_start, len(body)):
        if body[i] == '{': cnt += 1
        elif body[i] == '}':
            cnt -= 1
            if cnt == 0:
                try:
                    d = json.loads(body[obj_start:i+1])
                    return d.get("results", [])
                except:
                    return []
    return []

print("Running Metrocuadrado multi-slug extraction sweep...")
all_items = {}
for slug, barrio, zone in neighborhood_slugs:
    url = f"https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/{slug}/"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            body = resp.read().decode('utf-8', errors='ignore')
            items = parse_rsc(body)
            for itm in items:
                mapped = map_metro_item(itm, barrio, zone)
                if mapped:
                    all_items[mapped["id"]] = mapped
        time.sleep(0.3)
    except Exception as e:
        print(f"Warning on {slug}: {e}")

print(f"Total unique valid properties under $2.5M COP: {len(all_items)}")
dataset = list(all_items.values())
with open(".agents/explorer_m1_1/metrocuadrado_sample_dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2, ensure_ascii=False)
print("Saved to .agents/explorer_m1_1/metrocuadrado_sample_dataset.json")
