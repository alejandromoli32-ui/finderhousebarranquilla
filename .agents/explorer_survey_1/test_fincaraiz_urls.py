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

test_urls = [
    "https://www.fincaraiz.com.co/arriendo/apartamentos/barranquilla/atlantico",
    "https://www.fincaraiz.com.co/arriendo/apartamentos/barranquilla/atlantico?precioHasta=2500000",
    "https://www.fincaraiz.com.co/arriendo/apartamentos/barranquilla/atlantico?price_to=2500000",
    "https://www.fincaraiz.com.co/arriendo/apartamentos/riomar/barranquilla",
    "https://www.fincaraiz.com.co/arriendo/apartamentos/el-golf/barranquilla",
    "https://www.fincaraiz.com.co/arriendo/apartamentos/villa-santos/barranquilla"
]

for url in test_urls:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            # find searchFast
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
            found = False
            for s in scripts:
                if '"searchFast"' in s:
                    data = json.loads(s)
                    sf = data.get("props", {}).get("pageProps", {}).get("fetchResult", {}).get("searchFast", {})
                    items = sf.get("data", [])
                    paginator = sf.get("paginatorInfo", {})
                    total = paginator.get("total", len(items))
                    print(f"[OK] {url.split('.co')[-1]} -> Status: {resp.status}, Total in DB: {total}, Items returned: {len(items)}")
                    if items:
                        sample_prices = [it.get('price', {}).get('amount') for it in items[:5]]
                        print(f"     Sample prices: {sample_prices}")
                    found = True
                    break
            if not found:
                print(f"[NO_JSON] {url.split('.co')[-1]} -> Status: {resp.status}, HTML len: {len(html)}")
    except urllib.error.HTTPError as e:
        print(f"[{e.code}] {url.split('.co')[-1]} -> HTTP Error: {e.reason}")
    except Exception as e:
        print(f"[ERR] {url.split('.co')[-1]} -> {e}")
