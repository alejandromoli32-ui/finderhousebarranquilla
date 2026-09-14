import re
from pathlib import Path

web_files = list(Path("web").glob("*"))
external_refs = []
for wf in web_files:
    if wf.is_file():
        txt = wf.read_text(encoding="utf-8", errors="ignore")
        matches = re.findall(r"https?://[^\s\"\'\<\>]+", txt)
        for m in matches:
            if not any(allowed in m for allowed in ["wa.me", "whatsapp.com", "fincaraiz.com.co", "metrocuadrado.com", "ciencuadras.com", "localhost", "127.0.0.1"]):
                external_refs.append((str(wf), m))

print(f"External references in web/ (excluding listing links and localhost): {len(external_refs)}")
for ref in external_refs:
    print(f"  {ref[0]}: {ref[1]}")
