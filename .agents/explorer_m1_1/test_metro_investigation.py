import json
import re

with open(".agents/explorer_survey_1/metrocuadrado_rsc.txt", "r", encoding="utf-8") as f:
    text = f.read()

print(f"RSC total length: {len(text)}")

# Check keys surrounding results
start_idx = text.find('"results":[')
if start_idx != -1:
    before = text[max(0, start_idx-300):start_idx]
    print("--- 300 chars before 'results': ---")
    print(before)

# Search for totalResults or total or pagination
for k in ["totalResults", "totalPages", "total", "page", "currentPage", "numPages"]:
    matches = [m.start() for m in re.finditer(re.escape(k), text)]
    print(f"Key '{k}': {len(matches)} occurrences")
    for m in matches[:5]:
        print("   Snippet:", text[max(0, m-40):m+80])

# Check if there are other keys at the same level as results
# Let's find what object contains results
# Find opening bracket before results
pos = start_idx
while pos > 0 and text[pos] != '{':
    pos -= 1
print(f"Nearest '{{' before results is at {pos}, slice from pos to start_idx:")
print(text[pos:start_idx+15])
