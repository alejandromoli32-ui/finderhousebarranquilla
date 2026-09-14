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

url = "https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/?priceTo=2500000"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

print("Metrocuadrado HTML Length:", len(html))

# Check for JSON objects in script tags
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Total scripts in Metrocuadrado: {len(scripts)}")
for i, s in enumerate(scripts):
    if len(s) > 1000 and any(w in s for w in ['results', 'inmuebles', 'properties', 'realestate', 'listings', 'data']):
        print(f"  Script {i}: length {len(s)}")
        # Check if it starts with var or window or is JSON
        preview = s[:300].replace('\n', ' ')
        print(f"    Preview: {preview}")
        if "results" in s or "inmueble" in s or "m2" in s:
            with open(f".agents/explorer_survey_1/metrocuadrado_script_{i}.txt", "w", encoding="utf-8") as f_out:
                f_out.write(s[:20000])

# Check for listing card elements in HTML
# e.g., class names or data-testid or custom tags
card_classes = set(re.findall(r'class="([^"]*(?:card|item|property|inmueble)[^"]*)"', html, re.IGNORECASE))
print(f"\nCard-related CSS classes ({len(card_classes)} found):")
for c in list(card_classes)[:15]:
    print("  -", c)

# Let's also check for JSON-LD in Metrocuadrado
json_lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
print(f"\nJSON-LD blocks in Metrocuadrado: {len(json_lds)}")
for i, jld in enumerate(json_lds):
    try:
        jd = json.loads(jld)
        print(f"  JSON-LD {i}: @type = {jd.get('@type')}")
        if jd.get('@type') in ['ItemList', 'SearchResultsPage', 'Product']:
            print(json.dumps(jd, indent=2)[:500])
    except Exception as e:
        print(f"  JSON-LD {i} parse error: {e}")
