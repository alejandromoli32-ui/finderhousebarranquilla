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

def fetch_and_parse(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            # Look for __next_f
            matches = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', html)
            combined = ""
            for m in matches:
                try:
                    combined += json.loads(f'"{m}"')
                except:
                    combined += m
            # find initialResults
            start_pos = combined.find('"initialResults":{')
            if start_pos == -1:
                return {"error": "initialResults not found", "html_len": len(html)}
            obj_start = start_pos + len('"initialResults":')
            cnt = 0
            obj_end = -1
            for i in range(obj_start, len(combined)):
                if combined[i] == '{': cnt += 1
                elif combined[i] == '}':
                    cnt -= 1
                    if cnt == 0:
                        obj_end = i + 1
                        break
            if obj_end != -1:
                data = json.loads(combined[obj_start:obj_end])
                results = data.get("results", [])
                totalHits = data.get("totalHits")
                from_val = data.get("filters", {}).get("from")
                return {
                    "totalHits": totalHits,
                    "from": from_val,
                    "count": len(results),
                    "first_id": results[0].get("midinmueble") if results else None,
                    "last_id": results[-1].get("midinmueble") if results else None,
                }
    except Exception as e:
        return {"error": str(e)}

print("Test 1: Miramar page 1 (default)")
res1 = fetch_and_parse("https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/miramar/")
print("Res 1:", res1)

print("Test 2: Miramar with ?from=50")
res2 = fetch_and_parse("https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/miramar/?from=50")
print("Res 2:", res2)

print("Test 3: Miramar with ?page=2")
res3 = fetch_and_parse("https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/miramar/?page=2")
print("Res 3:", res3)
