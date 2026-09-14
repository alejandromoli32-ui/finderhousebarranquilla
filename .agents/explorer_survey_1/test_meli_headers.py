import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://inmuebles.mercadolibre.com.co/inmuebles/arriendo/atlantico/barranquilla/_OrderId_PRICE*ASC_PriceRange_0COP-2500000COP"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "es-419,es;q=0.9",
    "Accept-Encoding": "identity",
    "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        print("Status:", resp.status)
        print("Final URL:", resp.url)
        content = resp.read().decode('utf-8', errors='ignore')
        print("Content length:", len(content))
        if "account-verification" in resp.url:
            print("MercadoLibre requires bot verification (CAPTCHA/Challenge)")
        else:
            print("Successfully bypassed or loaded!")
            with open(".agents/explorer_survey_1/meli_sample.html", "w", encoding="utf-8") as f:
                f.write(content[:20000])
except Exception as e:
    print("Error:", e)
