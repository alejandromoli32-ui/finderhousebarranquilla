import json
import ssl
import urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

with open("data/inmuebles_barranquilla.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Sample 5 Metrocuadrado and 5 Finca Raiz listings
mq_samples = [p for p in data if "metrocuadrado.com" in p.get("url", "")][:5]
fr_samples = [p for p in data if "fincaraiz.com.co" in p.get("url", "")][:5]
samples = mq_samples + fr_samples

print(f"Testing {len(samples)} sample URLs...")
for p in samples:
    url = p["url"]
    portal = p["portal"]
    pid = p["id"]
    try:
        req = urllib.request.Request(url, headers=headers, method="HEAD")
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            print(f"[{resp.status}] {pid} ({portal}): {url[:70]}...")
    except urllib.error.HTTPError as e:
        # If HEAD not allowed (403/405), try GET with minimal read
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                print(f"[{resp.status} (GET)] {pid} ({portal}): {url[:70]}...")
        except Exception as e2:
            print(f"[ERR] {pid} ({portal}) HTTP {e.code} / {e2}: {url[:70]}...")
    except Exception as e:
        print(f"[ERR] {pid} ({portal}): {e}: {url[:70]}...")
