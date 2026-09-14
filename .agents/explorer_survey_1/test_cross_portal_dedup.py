import urllib.request
import ssl
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_metro_barrio(barrio):
    url = f"https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/{barrio}/"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        matches = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', html)
        combined = ""
        for m in matches:
            try: combined += json.loads(f'"{m}"')
            except: combined += m
        start = combined.find('"results":[')
        if start == -1: return []
        arr_start = start + len('"results":')
        cnt = 0
        end = -1
        for i in range(arr_start, len(combined)):
            if combined[i] == '[': cnt += 1
            elif combined[i] == ']':
                cnt -= 1
                if cnt == 0:
                    end = i + 1
                    break
        if end == -1: return []
        raw_items = json.loads(combined[arr_start:end])
        clean = []
        for r in raw_items:
            canon = float(r.get('mvalorarriendo') or 0)
            admin = 0
            try:
                admin = float(r.get('data', {}).get('mvaloradministracion') or 0)
            except:
                pass
            total = canon + admin
            if 0 < total <= 2500000:
                clean.append({
                    "portal": "metrocuadrado",
                    "id": f"metro_{r.get('midinmueble')}",
                    "title": r.get('title'),
                    "property_type": r.get('mtipoinmueble', {}).get('nombre', 'Apartamento'),
                    "canon": int(canon),
                    "admin_fee": int(admin),
                    "total_price": int(total),
                    "neighborhood": r.get('mnombrecomunbarrio') or barrio,
                    "area_m2": float(r.get('marea') or 0),
                    "bedrooms": int(r.get('mnrocuartos') or 0),
                    "bathrooms": int(r.get('mnrobanos') or 0),
                    "parking": int(r.get('mnrogarajes') or 0),
                    "images": [r.get('imageLink')] if r.get('imageLink') else [],
                    "url": f"https://www.metrocuadrado.com{r.get('link')}",
                    "contact_phone": r.get('contactPhone'),
                    "whatsapp": r.get('whatsapp'),
                    "agency": r.get('data', {}).get('mnombrevisitor') or r.get('midempresa')
                })
        return clean
    except Exception as e:
        print(f"Error fetching Metrocuadrado {barrio}: {e}")
        return []

def get_fincaraiz_barrio(barrio):
    url = f"https://www.fincaraiz.com.co/arriendo/apartamentos/{barrio}/barranquilla"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        for s in scripts:
            if '"searchFast"' in s:
                data = json.loads(s)
                sf = data.get("props", {}).get("pageProps", {}).get("fetchResult", {}).get("searchFast", {})
                raw_items = sf.get("data", [])
                clean = []
                for itm in raw_items:
                    price_obj = itm.get('price', {})
                    canon = float(price_obj.get('amount') or 0)
                    admin = float(itm.get('commonExpenses') or 0)
                    total = canon + admin if admin else canon
                    if 0 < total <= 2500000:
                        # Extract bedrooms, bathrooms, etc. from technicalSheet
                        tech = {t.get('field'): t.get('value') for t in itm.get('technicalSheet', [])}
                        clean.append({
                            "portal": "fincaraiz",
                            "id": f"finca_{itm.get('id')}",
                            "title": itm.get('title'),
                            "property_type": "Apartamento",
                            "canon": int(canon),
                            "admin_fee": int(admin),
                            "total_price": int(total),
                            "neighborhood": itm.get('locations', {}).get('location_main', {}).get('name') or barrio,
                            "area_m2": float(itm.get('m2') or itm.get('m2Built') or 0),
                            "bedrooms": int(tech.get('bedrooms') or itm.get('bedrooms') or 0),
                            "bathrooms": int(tech.get('bathrooms') or itm.get('bathrooms') or 0),
                            "parking": int(tech.get('garage') or itm.get('garage') or 0),
                            "images": [img.get('image') for img in itm.get('images', []) if img.get('image')],
                            "url": f"https://www.fincaraiz.com.co{itm.get('link')}",
                            "contact_phone": itm.get('owner', {}).get('masked_phone') if itm.get('owner') else None,
                            "whatsapp": itm.get('owner', {}).get('whatsapp_phone') if itm.get('owner') else None,
                            "agency": itm.get('owner', {}).get('name') if itm.get('owner') else None
                        })
                return clean
        return []
    except Exception as e:
        print(f"Error fetching FincaRaiz {barrio}: {e}")
        return []

print("Extracting sample dataset for Miramar and Villa Carolina...")
metro_miramar = get_metro_barrio("miramar")
finca_miramar = get_fincaraiz_barrio("miramar")

print(f"Metrocuadrado Miramar <= $2.5M: {len(metro_miramar)} listings")
print(f"Finca Raiz Miramar <= $2.5M: {len(finca_miramar)} listings")

# Check for potential duplicates
print("\nChecking cross-portal overlap...")
all_miramar = metro_miramar + finca_miramar
potential_dups = []
for i in range(len(all_miramar)):
    for j in range(i + 1, len(all_miramar)):
        a, b = all_miramar[i], all_miramar[j]
        if a['portal'] != b['portal']:
            # Compare specs:
            price_diff = abs(a['total_price'] - b['total_price'])
            area_diff = abs(a['area_m2'] - b['area_m2'])
            same_rooms = a['bedrooms'] == b['bedrooms'] and a['bedrooms'] > 0
            same_baths = a['bathrooms'] == b['bathrooms'] and a['bathrooms'] > 0
            if price_diff <= 100000 and area_diff <= 5 and same_rooms:
                potential_dups.append((a, b, price_diff, area_diff))

print(f"Potential cross-portal duplicates found: {len(potential_dups)}")
for a, b, pdiff, adiff in potential_dups[:5]:
    print(f"\nMatch: {a['portal']} vs {b['portal']}")
    print(f"  A: {a['title']} | ${a['total_price']:,} | {a['area_m2']}m2 | {a['bedrooms']}R/{a['bathrooms']}B")
    print(f"  B: {b['title']} | ${b['total_price']:,} | {b['area_m2']}m2 | {b['bedrooms']}R/{b['bathrooms']}B")
    print(f"  URL A: {a['url']}")
    print(f"  URL B: {b['url']}")

# Save sample dataset
with open(".agents/explorer_survey_1/sample_miramar_dataset.json", "w", encoding="utf-8") as f_out:
    json.dump({"metro": metro_miramar, "finca": finca_miramar, "potential_dups_count": len(potential_dups)}, f_out, indent=2)
print("\nSaved sample dataset to sample_miramar_dataset.json")
