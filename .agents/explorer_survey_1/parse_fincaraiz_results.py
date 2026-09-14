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

url = "https://www.fincaraiz.com.co/arriendo/casas-y-apartamentos/barranquilla/atlantico?precioHasta=2500000"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for idx, s in enumerate(scripts):
    if '"props"' in s and '"pageProps"' in s:
        data = json.loads(s)
        pageProps = data.get("props", {}).get("pageProps", {})
        fetchResult = pageProps.get("fetchResult", {})
        print("fetchResult keys:", list(fetchResult.keys()))
        sf = fetchResult.get("searchFast", {})
        print("searchFast keys:", list(sf.keys()))
        results = sf.get("results", {})
        print("results keys:", list(results.keys()))
        hits = results.get("hits", []) or results.get("data", [])
        print(f"hits count: {len(hits)}")
        if hits:
            sample = hits[0]
            print("\nSample hit fields in searchFast:")
            print(json.dumps({k: sample[k] for k in list(sample.keys())[:15]}, indent=2))
            with open(".agents/explorer_survey_1/fincaraiz_sample_hit.json", "w", encoding="utf-8") as f_out:
                json.dump(sample, f_out, indent=2)
            print("Successfully saved full sample hit to fincaraiz_sample_hit.json!")
        break
