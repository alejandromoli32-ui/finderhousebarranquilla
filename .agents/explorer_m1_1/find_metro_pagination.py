import urllib.request
import ssl
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/miramar/"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# Search for hrefs containing pagination or numbers
hrefs = re.findall(r'href=[\'"]([^\'"]*miramar[^\'"]*)[\'"]', html)
print(f"Hrefs containing 'miramar': {len(hrefs)}")
unique_hrefs = list(set(hrefs))
for h in sorted(unique_hrefs)[:20]:
    print("  ", h)

# Search for any href with 'page' or 'pagina' or numbers
pagination_hrefs = re.findall(r'href=[\'"]([^\'"]*(?:pag|page|from)[^\'"]*)[\'"]', html, re.IGNORECASE)
print(f"Hrefs with pag/page/from: {len(pagination_hrefs)}")
for ph in list(set(pagination_hrefs))[:20]:
    print("  ", ph)

# Search in the RSC stream text for pagination URLs or NextPage
matches = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', html)
combined = "".join(matches)
p_matches = re.findall(r'[\'"][^\'"]*barranquilla/miramar[^\'"]*[\'"]', combined)
print(f"RSC strings matching barranquilla/miramar: {len(p_matches)}")
for pm in list(set(p_matches))[:20]:
    print("  RSC url:", pm)

# Let's also check for any pagination component or function in the RSC string
print("\nSearching for Pagination terms in RSC:")
for term in ['pagination', 'Pagination', 'totalPages', 'currentPage', 'handlePage', 'nextPage', 'page-item', 'pageNumber']:
    if term in combined:
        idx = combined.find(term)
        print(f"Found {term}:", combined[max(0, idx-50):idx+150])
