import urllib.request
import urllib.error
import ssl

targets = [
    ("Metrocuadrado Home", "https://www.metrocuadrado.com/"),
    ("Metrocuadrado Barranquilla", "https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/?priceTo=2500000"),
    ("Finca Raiz Home", "https://www.fincaraiz.com.co/"),
    ("Finca Raiz Barranquilla", "https://www.fincaraiz.com.co/arriendo/apartamentos-y-casas/barranquilla?precioHasta=2500000"),
    ("Ciencuadras Home", "https://www.ciencuadras.com/"),
    ("Ciencuadras Barranquilla", "https://www.ciencuadras.com/arriendo/inmuebles/barranquilla?precio-hasta=2500000"),
    ("MercadoLibre Inmuebles", "https://inmuebles.mercadolibre.com.co/inmuebles/arriendo/atlantico/barranquilla/_OrderId_PRICE*ASC_PriceRange_0COP-2500000COP"),
    ("Properati Home", "https://www.properati.com.co/"),
    ("Properati Barranquilla", "https://www.properati.com.co/s/barranquilla/alquiler")
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

print("Probing portals with urllib...")
for name, url in targets:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            content = resp.read()
            print(f"[{resp.status}] {name} -> Final URL: {resp.url} (Length: {len(content)})")
            server = resp.headers.get("Server", "unknown")
            cf_ray = resp.headers.get("CF-RAY", None)
            print(f"    Server: {server} | CF-Ray: {cf_ray}")
    except urllib.error.HTTPError as e:
        print(f"[{e.code}] {name} -> HTTP Error: {e.reason}")
        server = e.headers.get("Server", "unknown")
        cf_ray = e.headers.get("CF-RAY", None)
        print(f"    Server: {server} | CF-Ray: {cf_ray}")
    except Exception as e:
        print(f"[ERR] {name} -> {type(e).__name__}: {e}")
