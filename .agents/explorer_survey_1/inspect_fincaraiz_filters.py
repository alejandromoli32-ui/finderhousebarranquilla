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

url = "https://www.fincaraiz.com.co/arriendo/casas-y-apartamentos/barranquilla/atlantico"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for s in scripts:
    if '"props"' in s and '"pageProps"' in s:
        data = json.loads(s)
        params = data.get("props", {}).get("pageProps", {}).get("params", {})
        print("Params:")
        print(json.dumps(params, indent=2))
        filters_ctx = data.get("props", {}).get("pageProps", {}).get("FiltersContextInitialState", {})
        print("\nFiltersContextInitialState:")
        print(json.dumps(filters_ctx, indent=2))
        break
