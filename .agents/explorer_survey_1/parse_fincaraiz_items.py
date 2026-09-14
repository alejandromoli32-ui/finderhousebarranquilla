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
        sf = data.get("props", {}).get("pageProps", {}).get("fetchResult", {}).get("searchFast", {})
        paginator = sf.get("paginatorInfo", {})
        print("Paginator info:", json.dumps(paginator, indent=2))
        data_list = sf.get("data", [])
        print(f"data_list length: {len(data_list)}")
        if data_list:
            print("First item keys:", list(data_list[0].keys()))
            with open(".agents/explorer_survey_1/fincaraiz_sample_item.json", "w", encoding="utf-8") as f_out:
                json.dump(data_list[0], f_out, indent=2)
            print("Successfully saved sample item to fincaraiz_sample_item.json!")
            
            # Print key fields from first 3 items
            for i, itm in enumerate(data_list[:3]):
                print(f"\n--- Item {i} ---")
                print(f"ID: {itm.get('id')}")
                print(f"Title: {itm.get('title')}")
                print(f"Price: {itm.get('price')}")
                print(f"Admin: {itm.get('admin') or itm.get('administration') or itm.get('admin_price')}")
                print(f"Location: {itm.get('locations') or itm.get('address') or itm.get('neighbourhood')}")
                print(f"Bedrooms: {itm.get('bedrooms')}, Bathrooms: {itm.get('bathrooms')}, Garages: {itm.get('garages')}")
                print(f"Area: {itm.get('area')} / {itm.get('built_area')}")
                print(f"URL: {itm.get('link') or itm.get('url') or itm.get('slug')}")
        break
