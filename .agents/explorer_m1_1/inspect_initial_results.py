import json

with open(".agents/explorer_survey_1/metrocuadrado_rsc.txt", "r", encoding="utf-8") as f:
    text = f.read()

start_pos = text.find('"initialResults":{')
if start_pos != -1:
    obj_start = start_pos + len('"initialResults":')
    # Count braces to find where initialResults ends
    cnt = 0
    obj_end = -1
    for i in range(obj_start, len(text)):
        if text[i] == '{': cnt += 1
        elif text[i] == '}':
            cnt -= 1
            if cnt == 0:
                obj_end = i + 1
                break
    
    if obj_end != -1:
        initial_results_str = text[obj_start:obj_end]
        data = json.loads(initial_results_str)
        print("Keys of initialResults:", list(data.keys()))
        print("totalHits:", data.get("totalHits"))
        print("totalEntries:", data.get("totalEntries"))
        print("Number of items in results:", len(data.get("results", [])))
        # Check other keys besides results
        for k in data:
            if k != "results":
                print(f"  {k}: {data[k]}")
