import urllib.request
import ssl
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://www.metrocuadrado.com/_next/static/chunks/app/%5B%5B...filter%5D%5D/page-6aab6ea513004c91.js"
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        content = resp.read().decode('utf-8', errors='ignore')
        print(f"Downloaded filter page chunk, size: {len(content)}")
        with open(".agents/explorer_m1_1/filter_page_chunk.js", "w", encoding="utf-8") as f:
            f.write(content)
        
        # Search for page or pagination
        matches = re.findall(r'.{0,60}(?:pagination|from|page|currentPage|handlePage).{0,60}', content, re.IGNORECASE)
        print(f"Found {len(matches)} matches")
        for m in matches[:10]:
            print("  ", m.replace("\n", " "))
except Exception as e:
    print("Error fetching chunk:", e)
