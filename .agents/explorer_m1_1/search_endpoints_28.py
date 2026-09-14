with open(".agents/explorer_survey_1/metrocuadrado_script_28.txt", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

pos = text.find("P1MfFHfQMOtL16Zpg36NcntJYCLFm8FqFfudnavl")
if pos != -1:
    print("Around apiKey:")
    print(text[max(0, pos-100):pos+600])

# Also search for 'fetch(' or 'axios' or 'get(' or 'post('
for term in ['/api/', 'search?', 'search/', 'properties', 'inmuebles']:
    idx = 0
    matches = []
    while True:
        idx = text.find(term, idx)
        if idx == -1: break
        matches.append(text[max(0, idx-40):idx+80])
        idx += len(term)
        if len(matches) > 10: break
    if matches:
        print(f"\nMatches for {term}:")
        for m in matches[:3]:
            print("  ", m.replace("\n", " "))
