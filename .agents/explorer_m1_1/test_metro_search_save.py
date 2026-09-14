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

def test_url(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    matches = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', html)
    combined = ""
    for m in matches:
        try: combined += json.loads(f'"{m}"')
        except: combined += m
    start_pos = combined.find('"initialResults":{')
    if start_pos == -1:
        return "No initialResults"
    obj_start = start_pos + len('"initialResults":')
    cnt = 0
    for i in range(obj_start, len(combined)):
        if combined[i] == '{': cnt += 1
        elif combined[i] == '}':
            cnt -= 1
            if cnt == 0:
                obj_end = i + 1
                break
    data = json.loads(combined[obj_start:obj_end])
    res = data.get("results", [])
    from_val = data.get("filters", {}).get("from")
    totalHits = data.get("totalHits")
    return {
        "from": from_val,
        "totalHits": totalHits,
        "count": len(res),
        "first_id": res[0].get("midinmueble") if res else None,
        "first_title": res[0].get("title") if res else None
    }

url1 = "https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/miramar/?search=save&from=0"
url2 = "https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/miramar/?search=save&from=50"
url3 = "https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/miramar/?search=save&from=1"

print("Test 1 (from=0):", test_url(url1))
print("Test 2 (from=50):", test_url(url2))
print("Test 3 (from=1):", test_url(url3))
