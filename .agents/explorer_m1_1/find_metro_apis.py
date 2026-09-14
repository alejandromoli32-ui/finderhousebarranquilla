import os
import glob
import re

files = glob.glob(".agents/explorer_survey_1/metrocuadrado*.txt")
print("Found files:", files)

for fpath in files:
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    apis = re.findall(r'https?://[^\s"\'<>]+(?:api|search|inmueble|filter)[^\s"\'<>]*', content, re.IGNORECASE)
    if apis:
        print(f"\nIn {fpath}:")
        for a in list(set(apis))[:10]:
            print("  ", a)
    
    # check for internal api routes like /api/...
    internal_apis = re.findall(r'[\'"](/api/[^\'"]+)[\'"]', content)
    if internal_apis:
        print(f"\nInternal APIs in {fpath}:")
        for ia in list(set(internal_apis)):
            print("  ", ia)
