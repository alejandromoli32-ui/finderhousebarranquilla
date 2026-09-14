import glob
import re

files = glob.glob(".agents/explorer_survey_1/metrocuadrado*.txt")

for fpath in files:
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    
    # search for pagination logic
    matches = re.findall(r'.{0,100}(?:pagination|paginate|from\s*[:=]|currentPage|selectedPage).{0,100}', text, re.IGNORECASE)
    if matches:
        print(f"\n--- In {fpath} ({len(matches)} matches) ---")
        for m in matches[:5]:
            print("  ", m.strip().replace("\n", " "))
