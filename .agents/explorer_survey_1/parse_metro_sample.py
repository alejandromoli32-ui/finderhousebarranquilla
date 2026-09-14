import json
import re

with open(".agents/explorer_survey_1/metrocuadrado_rsc.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Find the JSON array under "results":
start_idx = text.find('"results":[')
if start_idx != -1:
    array_start = start_idx + len('"results":')
    # Find matching closing bracket
    bracket_count = 0
    end_idx = -1
    for i in range(array_start, len(text)):
        if text[i] == '[':
            bracket_count += 1
        elif text[i] == ']':
            bracket_count -= 1
            if bracket_count == 0:
                end_idx = i + 1
                break
    
    if end_idx != -1:
        results_json_str = text[array_start:end_idx]
        print(f"Extracted results array string length: {len(results_json_str)}")
        try:
            results = json.loads(results_json_str)
            print(f"Total results parsed from Metrocuadrado: {len(results)}")
            if results:
                sample = results[0]
                print("\nSample Metrocuadrado item keys:", list(sample.keys()))
                with open(".agents/explorer_survey_1/metrocuadrado_sample_item.json", "w", encoding="utf-8") as f_out:
                    json.dump(sample, f_out, indent=2)
                print("Saved to .agents/explorer_survey_1/metrocuadrado_sample_item.json")
                
                for idx, r in enumerate(results[:5]):
                    print(f"\n--- Metrocuadrado {idx} ---")
                    print(f"Title: {r.get('title')}")
                    print(f"Price: {r.get('price')} / Canon: {r.get('mvalorventa') or r.get('mcanon')}")
                    print(f"Admin: {r.get('data', {}).get('mvaloradministracion')}")
                    print(f"Phone: {r.get('contactPhone')} | WhatsApp: {r.get('whatsapp')}")
                    print(f"Barrio: {r.get('mnombrecomunbarrio')} / {r.get('mciudad')}")
                    print(f"Rooms: {r.get('mhabitaciones') or r.get('rooms')} | Baths: {r.get('mbanos') or r.get('baths')}")
                    print(f"Area: {r.get('marea') or r.get('area')}")
                    print(f"Link: https://www.metrocuadrado.com{r.get('link')}")
        except Exception as e:
            print("JSON parse error:", e)
