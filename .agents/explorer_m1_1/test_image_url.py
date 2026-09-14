import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

sample_mid = "21602-M6953598"
sample_photo = "21602-M6953598_1"

suffixes = ["_p.jpg", "_f.jpg", "_m.jpg", ".jpg"]
for s in suffixes:
    url = f"https://multimedia.metrocuadrado.com/{sample_mid}/{sample_photo}{s}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            print(f"Suffix {s}: HTTP {resp.status}, Content-Type: {resp.headers.get('Content-Type')}, Length: {resp.headers.get('Content-Length')}")
    except Exception as e:
        print(f"Suffix {s}: Error {e}")
