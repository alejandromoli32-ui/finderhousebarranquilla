import urllib.request
import ssl
import re
import json
import html

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://www.ciencuadras.com/arriendo/apartamento-casa/barranquilla?precio-hasta=2500000"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    page_html = resp.read().decode('utf-8', errors='ignore')

scripts = re.findall(r'<script[^>]*>(.*?)</script>', page_html, re.DOTALL)
print(f"Total scripts: {len(scripts)}")

# Inspect script 3 (ItemList JSON-LD)
if len(scripts) > 3:
    try:
        data3 = json.loads(scripts[3])
        print("Script 3 JSON-LD parsed:")
        print("Type:", data3.get("@type"))
        print("Items count:", data3.get("numberOfItems"))
        items = data3.get("itemListElement", [])
        if items:
            print("First item in Script 3:")
            print(json.dumps(items[0], indent=2))
            with open(".agents/explorer_survey_1/ciencuadras_sample_item.json", "w", encoding="utf-8") as f_out:
                json.dump(items[0], f_out, indent=2)
    except Exception as e:
        print("Error parsing script 3:", e)

# Inspect script 6 (Angular Universal transfer state)
for idx, s in enumerate(scripts):
    if "&q;" in s or "TRANSFER_STATE" in s or "transfer-state" in s:
        print(f"Script {idx} has transfer state (len {len(s)})")
        decoded_s = html.unescape(s)
        try:
            state_data = json.loads(decoded_s)
            print("Successfully parsed transfer state as JSON!")
            print("Transfer state top keys:", list(state_data.keys()))
            with open(f".agents/explorer_survey_1/ciencuadras_transfer_state_keys.json", "w", encoding="utf-8") as f_out:
                json.dump({"keys": list(state_data.keys())}, f_out, indent=2)
        except Exception as e:
            print("Could not parse transfer state JSON directly:", e)
