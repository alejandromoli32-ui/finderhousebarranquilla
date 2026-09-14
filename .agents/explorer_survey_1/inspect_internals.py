import urllib.request
import ssl
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = {
    "metrocuadrado": "https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/?priceTo=2500000",
    "fincaraiz": "https://www.fincaraiz.com.co/arriendo/casas-y-apartamentos/barranquilla/atlantico?precioHasta=2500000",
    "ciencuadras": "https://www.ciencuadras.com/arriendo/apartamento-casa/barranquilla?precio-hasta=2500000"
}

for name, url in urls.items():
    print(f"\n==================== Analyzing {name} ====================")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            print(f"HTML Length: {len(html)} chars")
            
            # Check for __NEXT_DATA__
            next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">({.*?})</script>', html, re.DOTALL)
            if next_data_match:
                print("FOUND __NEXT_DATA__!")
                data = json.loads(next_data_match.group(1))
                page = data.get("page", "")
                props = data.get("props", {})
                pageProps = props.get("pageProps", {})
                print(f"  Page: {page}")
                print(f"  pageProps keys: {list(pageProps.keys())}")
                # Save sample pageProps keys and structure
                with open(f".agents/explorer_survey_1/{name}_next_data_sample.json", "w", encoding="utf-8") as f:
                    # dump truncated/summary
                    json.dump({"page": page, "keys": list(pageProps.keys())}, f, indent=2)
            else:
                print("No __NEXT_DATA__ found")
                
            # Check for window.__INITIAL_STATE__ or similar
            initial_state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});</script>', html, re.DOTALL)
            if initial_state_match:
                print("FOUND window.__INITIAL_STATE__!")
                
            # Check for JSON-LD schema
            json_lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
            print(f"Found {len(json_lds)} JSON-LD blocks")
            for i, jld in enumerate(json_lds[:3]):
                try:
                    parsed_jld = json.loads(jld)
                    print(f"  JSON-LD {i}: @type = {parsed_jld.get('@type')} / keys: {list(parsed_jld.keys()) if isinstance(parsed_jld, dict) else type(parsed_jld)}")
                except:
                    print(f"  JSON-LD {i}: parsing failed")
                    
            # Check for API endpoints in scripts
            api_mentions = set(re.findall(r'https?://[a-zA-Z0-9\.-]+/(?:api|v[0-9]+|graphql|gateway)/[a-zA-Z0-9_\-\./]*', html))
            print(f"API endpoints mentioned in HTML/JS ({len(api_mentions)} found):")
            for api in list(api_mentions)[:8]:
                print(f"  - {api}")
                
    except Exception as e:
        print(f"Error analyzing {name}: {e}")
