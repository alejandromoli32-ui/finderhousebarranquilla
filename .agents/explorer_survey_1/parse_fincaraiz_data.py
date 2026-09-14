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

# Find the script tag containing pageProps
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for idx, s in enumerate(scripts):
    if '"props"' in s and '"pageProps"' in s:
        print(f"Found pageProps in script {idx} (Length: {len(s)})")
        try:
            data = json.loads(s)
            pageProps = data.get("props", {}).get("pageProps", {})
            print("pageProps keys:", list(pageProps.keys()))
            
            # Let's inspect each key
            for k in pageProps:
                val = pageProps[k]
                if isinstance(val, dict):
                    print(f"  {k}: dict with keys {list(val.keys())[:10]}")
                elif isinstance(val, list):
                    print(f"  {k}: list of len {len(val)}")
                else:
                    print(f"  {k}: {type(val)} = {str(val)[:50]}")
            
            # Check results / listings / initialReduxState
            for key in ["results", "listings", "properties", "searchResponse", "initialState", "data"]:
                if key in pageProps:
                    print(f"Found key in pageProps: {key}")
                    
            # Let's save a clean representation
            if "results" in pageProps:
                res = pageProps["results"]
                hits = res.get("hits", []) or res.get("data", []) or res.get("properties", [])
                print(f"Hits found: {len(hits)}")
                if hits:
                    print("First hit keys:", list(hits[0].keys()))
                    with open(".agents/explorer_survey_1/fincaraiz_sample_hit.json", "w", encoding="utf-8") as f:
                        json.dump(hits[0], f, indent=2)
                    print("Saved sample hit to .agents/explorer_survey_1/fincaraiz_sample_hit.json")
        except Exception as e:
            print("Parse error on script:", e)
