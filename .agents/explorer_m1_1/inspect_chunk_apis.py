with open(".agents/explorer_m1_1/filter_page_chunk.js", "r", encoding="utf-8") as f:
    text = f.read()

for term in ["apiUrl", "apiKey", "post(", "get(", "/api", "search"]:
    matches = []
    idx = 0
    while True:
        idx = text.find(term, idx)
        if idx == -1: break
        matches.append(text[max(0, idx-40):idx+80])
        idx += len(term)
        if len(matches) > 10: break
    if matches:
        print(f"\n--- Matches for '{term}' ---")
        for m in matches[:5]:
            print(" ", m.replace("\n", " "))
