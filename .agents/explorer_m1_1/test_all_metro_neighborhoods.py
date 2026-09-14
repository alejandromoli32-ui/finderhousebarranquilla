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

neighborhood_slugs = [
    "miramar",
    "villa-carolina",
    "villa-country",
    "alto-prado",
    "villa-santos",
    "riomar",
    "el-golf",
    "ciudad-mallorquin",
    "altos-de-riomar",
    "buenavista",
    "paraiso",
    "bellavista",
    "el-prado",
    "el-limoncito",
    "tabor",
    "los-alpes",
    "andalucia",
    "san-vicente",
    "la-campina",
    "la-cumbre"
]

def parse_rsc_results(rsc_text):
    start_pos = rsc_text.find('"initialResults":{')
    if start_pos == -1:
        # fallback to "results":[
        res_pos = rsc_text.find('"results":[')
        if res_pos == -1: return []
        arr_start = res_pos + len('"results":')
        cnt = 0
        end_idx = -1
        for i in range(arr_start, len(rsc_text)):
            if rsc_text[i] == '[': cnt += 1
            elif rsc_text[i] == ']':
                cnt -= 1
                if cnt == 0:
                    end_idx = i + 1
                    break
        if end_idx == -1: return []
        try: return json.loads(rsc_text[arr_start:end_idx])
        except: return []

    obj_start = start_pos + len('"initialResults":')
    cnt = 0
    obj_end = -1
    for i in range(obj_start, len(rsc_text)):
        if rsc_text[i] == '{': cnt += 1
        elif rsc_text[i] == '}':
            cnt -= 1
            if cnt == 0:
                obj_end = i + 1
                break
    if obj_end == -1: return []
    try:
        data = json.loads(rsc_text[obj_start:obj_end])
        return data.get("results", [])
    except Exception as e:
        return []

print(f"Testing {len(neighborhood_slugs)} neighborhoods in Barranquilla Norte...")
total_properties = 0
total_under_2_5m = 0
results_by_barrio = {}

for slug in neighborhood_slugs:
    url = f"https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/{slug}/"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            body = resp.read().decode('utf-8', errors='ignore')
            items = parse_rsc_results(body)
            valid = []
            for itm in items:
                canon = itm.get('mvalorarriendo') or 0
                admin = 0
                try:
                    admin_str = itm.get('data', {}).get('mvaloradministracion')
                    if admin_str:
                        admin = float(admin_str)
                except:
                    pass
                total = canon + admin
                if 0 < total <= 2500000:
                    valid.append(itm)
            
            total_properties += len(items)
            total_under_2_5m += len(valid)
            results_by_barrio[slug] = {
                "status": resp.status,
                "total_items": len(items),
                "under_2_5m": len(valid)
            }
            print(f"[{resp.status}] {slug:18}: {len(items):3} items | {len(valid):3} under $2.5M")
    except urllib.error.HTTPError as e:
        print(f"[{e.code}] {slug:18}: HTTPError {e.reason}")
    except Exception as e:
        print(f"[ERR] {slug:18}: {e}")

print("\n--- Summary ---")
print(f"Total properties retrieved: {total_properties}")
print(f"Total under $2.5M COP: {total_under_2_5m}")
