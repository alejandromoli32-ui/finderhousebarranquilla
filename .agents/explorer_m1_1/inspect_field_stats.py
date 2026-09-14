import urllib.request
import ssl
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/x-component",
    "RSC": "1",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/miramar/"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    body = resp.read().decode('utf-8', errors='ignore')

# parse RSC results
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

print(f"Inspecting {len(results)} items from Miramar...")
field_stats = {}
for itm in results:
    for k in [
        "midinmueble", "title", "mtipoinmueble", "mtiponegocio", "mvalorarriendo",
        "marea", "mareac", "mnrocuartos", "mnrobanos", "mnrogarajes",
        "mnombrecomunbarrio", "mbarrio", "mzona", "estrato",
        "contactPhone", "whatsapp", "imageLink", "mgaleriainmueble",
        "link", "data", "OwnerType", "midempresa", "comment", "geopoints"
    ]:
        val = itm.get(k)
        if k not in field_stats:
            field_stats[k] = {"present": 0, "null": 0, "types": set()}
        if val is not None:
            field_stats[k]["present"] += 1
            field_stats[k]["types"].add(type(val).__name__)
        else:
            field_stats[k]["null"] += 1

print("\n--- Field Availability in Miramar Results ---")
for k, v in field_stats.items():
    print(f"  {k:20}: present={v['present']:2}, null={v['null']:2}, types={list(v['types'])}")

# Check nested data fields
admin_vals = []
visitor_vals = []
for itm in results:
    d = itm.get('data') or {}
    admin_vals.append(d.get('mvaloradministracion'))
    visitor_vals.append(d.get('mnombrevisitor'))

print(f"\nadmin values sample: {admin_vals[:10]}")
print(f"visitor names sample: {visitor_vals[:10]}")
