import re
import urllib.request
import ssl

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

# Search for href links that look like pagination or filters
links = re.findall(r'href="([^"]*barranquilla[^"]*)"', html)
unique_links = sorted(list(set(links)))
print(f"Found {len(unique_links)} links with 'barranquilla':")
for l in unique_links[:25]:
    print(" ", l)

# Search for 'pagina' or 'page' or 'precio'
page_links = re.findall(r'href="([^"]*(?:pagina|page|precio|filter)[^"]*)"', html)
print(f"\nFound {len(page_links)} pagination/filter links:")
for l in sorted(list(set(page_links)))[:20]:
    print(" ", l)
