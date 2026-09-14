import urllib.request
import ssl
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/x-component",
    "RSC": "1",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/miramar/"
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        content_type = resp.headers.get("Content-Type")
        body = resp.read().decode('utf-8', errors='ignore')
        print(f"Status: {resp.status}, Content-Type: {content_type}, Body length: {len(body)}")
        print("First 300 chars of RSC stream:")
        print(body[:300])
        
        # Check if results are in raw stream
        has_results = '"results":[' in body
        print("Contains '\"results\":[':", has_results)
except Exception as e:
    print("Error:", e)
