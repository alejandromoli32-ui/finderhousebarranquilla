with open(".agents/explorer_survey_1/metrocuadrado_rsc.txt", "r", encoding="utf-8") as f:
    text = f.read()

pos = 0
while True:
    pos = text.find("totalResults", pos)
    if pos == -1:
        break
    print(f"\n--- Found totalResults at index {pos} ---")
    print(text[max(0, pos-150):pos+450])
    pos += 12

# Also search for 'results' or 'properties' or 'cards'
for keyword in ['"results":', '"properties":', '"data":', '"listings":', '"items":']:
    p = text.find(keyword)
    if p != -1:
        print(f"\n--- Found {keyword} at index {p} ---")
        print(text[max(0, p-50):p+300])
