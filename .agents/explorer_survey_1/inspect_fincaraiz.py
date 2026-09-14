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

def inspect_fincaraiz():
    url = "https://www.fincaraiz.com.co/arriendo/casas-y-apartamentos/barranquilla/atlantico?precioHasta=2500000"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        
    json_lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for i, jld in enumerate(json_lds):
        try:
            d = json.loads(jld)
            print(f"FincaRaiz JSON-LD {i}:")
            if d.get("@type") == "CollectionPage":
                mainEntity = d.get("mainEntity", {})
                print(f"  mainEntity type: {mainEntity.get('@type')}")
                itemList = mainEntity.get("itemListElement", [])
                print(f"  itemListElement count: {len(itemList)}")
                if itemList:
                    print("  Sample item 0:")
                    print(json.dumps(itemList[0], indent=2)[:1000])
        except Exception as e:
            print(f"  JSON-LD {i} parse error: {e}")

    # Check if there is another script tag with listing data
    script_matches = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    print(f"Total script tags in FincaRaiz: {len(script_matches)}")
    for idx, s in enumerate(script_matches):
        if "results" in s or "inmuebles" in s or "listings" in s or "properties" in s or "price" in s:
            if len(s) > 500:
                print(f"  Script {idx} length: {len(s)}, preview: {s[:200]}...")
                # save first matching large script to examine
                with open(f".agents/explorer_survey_1/fincaraiz_script_{idx}.txt", "w", encoding="utf-8") as f:
                    f.write(s[:50000])

inspect_fincaraiz()
