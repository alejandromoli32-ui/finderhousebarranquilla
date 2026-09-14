import json

with open(".agents/explorer_survey_1/fincaraiz_script_5.txt", "r", encoding="utf-8") as f:
    raw = f.read()

try:
    data = json.loads(raw)
    print("Successfully parsed Script 5 as JSON!")
    print("Top level keys:", list(data.keys()))
    pageProps = data.get("props", {}).get("pageProps", {})
    print("pageProps keys:", list(pageProps.keys()))
    
    # Check for results or hits
    for k in pageProps:
        val = pageProps[k]
        if isinstance(val, dict):
            print(f"pageProps[{k}] keys:", list(val.keys()))
        elif isinstance(val, list):
            print(f"pageProps[{k}] is list of length {len(val)}")
            
    # Look for listings/properties/hits
    results = pageProps.get("results", {}) or pageProps.get("hits", {}) or pageProps.get("properties", {})
    if isinstance(results, dict):
        print("results keys:", list(results.keys()))
        hits = results.get("hits", []) or results.get("data", []) or results.get("properties", [])
        print(f"hits count: {len(hits)}")
        if hits:
            sample = hits[0]
            print("\nSample hit keys:", list(sample.keys()))
            print("\nSample hit fields preview:")
            for field in ['id', 'title', 'price', 'administration', 'total_price', 'neighbourhood', 'area', 'bedrooms', 'bathrooms', 'garages', 'media', 'photos', 'url', 'client', 'contact']:
                if field in sample:
                    print(f"  {field}: {sample[field]}")
            # Save full sample hit
            with open(".agents/explorer_survey_1/fincaraiz_sample_hit.json", "w", encoding="utf-8") as f_out:
                json.dump(sample, f_out, indent=2)
                print("Saved sample hit to fincaraiz_sample_hit.json")
except Exception as e:
    print("Error:", e)
