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

url = "https://www.ciencuadras.com/arriendo/apartamento-casa/barranquilla?precio-hasta=2500000"
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    
    print("Ciencuadras HTML length:", len(html))
    
    # Check for Angular / React / Vue state
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    print(f"Total scripts in Ciencuadras: {len(scripts)}")
    for i, s in enumerate(scripts):
        if any(term in s for term in ['inmuebles', 'properties', 'results', 'searchResult', 'realEstate', 'canon', 'm2']):
            if len(s) > 1000:
                print(f"  Script {i} matches keywords (len {len(s)}): {s[:250].replace('\n', ' ')}")
                with open(f".agents/explorer_survey_1/ciencuadras_script_{i}.txt", "w", encoding="utf-8") as f_out:
                    f_out.write(s[:20000])

    # Check for API endpoints in Ciencuadras scripts
    apis = set(re.findall(r'https?://[a-zA-Z0-9\.-]+/(?:api|v[0-9]+|bff)/[a-zA-Z0-9_\-\./]*', html))
    print("APIs found in Ciencuadras:")
    for a in apis:
        print("  -", a)
except Exception as e:
    print("Error:", e)
