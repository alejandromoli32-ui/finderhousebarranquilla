import urllib.request
import ssl
import json
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

barrios = [
    "villa-santos",
    "alto-prado",
    "el-golf",
    "miramar",
    "villa-carolina",
    "riomar",
    "villa-country"
]

def parse_metro_results(html):
    next_f_matches = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', html)
    combined = ""
    for m in next_f_matches:
        try:
            combined += json.loads(f'"{m}"')
        except:
            combined += m
    start_idx = combined.find('"results":[')
    if start_idx == -1:
        return []
    arr_start = start_idx + len('"results":')
    cnt = 0
    end_idx = -1
    for i in range(arr_start, len(combined)):
        if combined[i] == '[': cnt += 1
        elif combined[i] == ']':
            cnt -= 1
            if cnt == 0:
                end_idx = i + 1
                break
    if end_idx == -1: return []
    try:
        return json.loads(combined[arr_start:end_idx])
    except:
        return []

print("Testing Metrocuadrado neighborhood URLs...")
for b in barrios:
    url = f"https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/{b}/"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            items = parse_metro_results(html)
            valid = 0
            for itm in items:
                c = itm.get('mvalorarriendo', 0)
                a = 0
                try:
                    a = float(itm.get('data', {}).get('mvaloradministracion') or 0)
                except:
                    pass
                if 0 < (c + a) <= 2500000:
                    valid += 1
            print(f"[{resp.status}] {b}: {len(items)} items returned, {valid} with total <= $2.5M")
    except Exception as e:
        print(f"[ERR] {b}: {e}")
