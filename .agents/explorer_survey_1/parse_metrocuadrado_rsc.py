import urllib.request
import ssl
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/?priceTo=2500000"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# Extract all self.__next_f.push chunks
next_f_matches = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', html)
print(f"Found {len(next_f_matches)} __next_f chunks")

combined_rsc = ""
for m in next_f_matches:
    # unescape json string
    try:
        chunk = json.loads(f'"{m}"')
        combined_rsc += chunk
    except Exception as e:
        combined_rsc += m

print(f"Total combined RSC string length: {len(combined_rsc)}")

# Search for property objects in RSC string
# Look for common keys in Metrocuadrado: m2, valor, canon, precio, habitaciones, banos, etc.
with open(".agents/explorer_survey_1/metrocuadrado_rsc.txt", "w", encoding="utf-8") as f:
    f.write(combined_rsc)

print("Saved combined RSC string to .agents/explorer_survey_1/metrocuadrado_rsc.txt")

# Let's search for JSON patterns or property structures
properties_match = re.findall(r'(\{"id":[^\{]+?"m2":[^\{]+?\})', combined_rsc)
print(f"Regex simple property matches: {len(properties_match)}")

# Check if there's an API call or JSON object with totalResults / properties
if "totalResults" in combined_rsc or "results" in combined_rsc:
    print("Found totalResults/results in RSC!")
    # let's search for snippet around results
    pos = combined_rsc.find("totalResults")
    if pos != -1:
        print("Around totalResults:", combined_rsc[max(0, pos-100):pos+300])

