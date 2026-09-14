import json
import urllib.request
import ssl

with open('data/inmuebles_barranquilla.json', 'r', encoding='utf-8') as f:
    listings = json.load(f)

print(f"Total listings: {len(listings)}")

indices = [0, 10, 30, 60, 90, 120, 150, 172]
for i in indices:
    p = listings[i]
    print(f"--- Index {i} ---")
    print(f"ID: {p.get('id')}")
    print(f"Portal: {p.get('portal')}")
    print(f"Title: {p.get('title')}")
    print(f"Neighborhood: {p.get('neighborhood')}, Zone: {p.get('zone')}")
    print(f"Price: Total=${p.get('total_price'):,} COP (Canon=${p.get('canon'):,}, Admin=${p.get('admin_fee'):,})")
    print(f"Specs: {p.get('bedrooms')} hab, {p.get('bathrooms')} bano, {p.get('area_m2')} m2, {p.get('parking')} parqueo")
    print(f"URL: {p.get('url')}")
    print(f"Contact: {p.get('contact')}")
    if p.get('images'):
        print(f"First Image: {p.get('images')[0]}")
    print(f"Description sample: {p.get('description', '')[:120]}...")
    print()

# Test connectivity to a sample of listing URLs and image URLs
print("=== Verifying Live URL Reachability (Sample) ===")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

sample_urls = [listings[i]['url'] for i in [0, 30, 60, 90, 120]]
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

for u in sample_urls:
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            print(f"URL: {u[:65]}... -> HTTP {resp.status}")
    except Exception as e:
        print(f"URL: {u[:65]}... -> Exception: {e}")

sample_imgs = [listings[i]['images'][0] for i in [0, 30, 60, 90, 120] if listings[i].get('images')]
for img in sample_imgs:
    try:
        req = urllib.request.Request(img, headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            print(f"IMG: {img[:65]}... -> HTTP {resp.status}, Content-Type: {resp.headers.get('Content-Type')}")
    except Exception as e:
        print(f"IMG: {img[:65]}... -> Exception: {e}")
