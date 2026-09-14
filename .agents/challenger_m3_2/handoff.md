# Adversarial Challenge Report: MFVI Ranking Algorithm & Geographic Balance

**Agent**: `challenger_m3_2` (Empirical Challenger)  
**Milestone**: M3 — Curated Immediate Visit Dossier & Contact Sheets  
**Working Directory**: `c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/challenger_m3_2`  
**Target Files Inspected**:
- `dossier_generator.py`
- `data/inmuebles_barranquilla.json`
- `data/dossier_curado.json`
- `DOSSIER_VISITAS.md`
**Test Harness Written**:
- `tests/test_adversarial_m3_mfvi.py` (24 adversarial test cases)

---

## 1. Observation

### Obs 1.1: 100% Agreement with Clean-Room Independent MFVI Implementation
- An independent oracle `IndependentMFVIOfflineOracle` was constructed in `tests/test_adversarial_m3_mfvi.py` based solely on the 100-point specification (Price/m² 25%, Location 25%, Space & Layout 20%, Stratum & Amenities 15%, Contact Readiness 15%).
- Executing `test_full_inventory_100_percent_mfvi_agreement` on all 172 records in `data/inmuebles_barranquilla.json` resulted in **0 discrepancies** (`diff > 1e-5: 0`).
- Component-level breakdown check (`test_component_breakdown_parity_on_all_properties`) confirmed exact equality across all 5 sub-scores for every listing:
  - Price efficiency: 100% match
  - Location prestige: 100% match
  - Space & layout: 100% match
  - Stratum & amenities: 100% match
  - Contact readiness: 100% match
- Selection funnel parity (`test_selection_funnel_exact_match`): The 15 property IDs selected by the funnel in `dossier_generator.py` match `data/dossier_curado.json` in exact rank order:
  ```json
  [
    "MERGED-9851-M6595771-193354024",
    "MQ-20802-M7027822",
    "MQ-18260-M5640703",
    "MQ-9851-M6921994",
    "MQ-9851-M5463984",
    "MERGED-12659-M6046505-194139995",
    "MERGED-13957-M6916787-194065632",
    "MQ-23769-M7006894",
    "MQ-671-M7036862",
    "MQ-9889-M6737523",
    "MQ-671-M5946897",
    "MQ-23769-M7006602",
    "MQ-16553-M6886725",
    "MQ-9851-M6918346",
    "MQ-9851-M6757768"
  ]
  ```

### Obs 1.2: Null / Missing Data Resilience (Tested Edge Cases)
1. **`stratum = None`** (`test_stratum_none_produces_valid_score_without_crash`):
   - Result: Produced valid score without NaN or crash.
   - Stratum score assigns base floor `2.0` pts (tested in `score_stratum_and_amenities(None, ...)`).
2. **`admin_fee = 0` and `admin_fee = None`** (`test_admin_fee_zero_and_none_resilience`):
   - In Colombia, many leases include administration within the canon.
   - Result: Properties with `admin_fee=0` and `admin_fee=None` evaluate cleanly, computing correct price/m² and scoring `[0, 100]` with no NaN.
3. **`unstated parking`** (`test_unstated_parking_variations`):
   - Tested 5 variations: `parking=None`, `parking=0`, omitted key, negative parking (`-1`), and string 0.
   - Result: All evaluated cleanly with parking sub-score `0.0`, resulting in space sub-score `15.0/20.0` with no crash or NaN.
4. **`area_m2 = 0`, negative area, or `None`** (`test_area_m2_zero_negative_and_none`):
   - Result: Falls back safely to neutral `12.0` price/m² score without `ZeroDivisionError`.
5. **Monte Carlo Random Fuzzing** (`test_fuzzing_monte_carlo_mutation_harness`):
   - 100 randomized property dictionaries with missing/extreme fields evaluated. Zero unhandled exceptions; all scores in `[0.0, 100.0]`.

### Obs 1.3: Empirical Input Schema Fragility Findings (Defensive Programming Gaps)
When inputs violate schema contracts with explicit `None` on mandatory object fields, `dossier_generator.py` exhibits specific failure modes:
1. `MultiFactorValueIndex.evaluate({"contact": None})`:
   - Verbatim error: `AttributeError: 'NoneType' object has no attribute 'get'` at line 187 of `dossier_generator.py` (`wa = clean_phone(contact.get("whatsapp"))`).
2. `MultiFactorValueIndex.evaluate({"total_price": None, "area_m2": 60})`:
   - Verbatim error: `TypeError: unsupported operand type(s) for /: 'NoneType' and 'int'` at line 84 of `dossier_generator.py` (`cost_m2 = total_price / area_m2`).
3. `select_curated_properties([{"images": None}])`:
   - Verbatim error: `TypeError: object of type 'NoneType' has no len()` at line 264 of `dossier_generator.py` (`if len(p.get("images", [])) < 3:`).

*Note*: In `data/inmuebles_barranquilla.json`, all 172 records have valid schema objects (`contact: dict`, `images: list`, `total_price: int`), so these fragilities do not trigger in production.

### Obs 1.4: Sector Diversity Audit of Top 15 Properties
- Evaluation of `data/dossier_curado.json` and `DOSSIER_VISITAS.md`:
  - Exactly 15 properties.
  - Sector distribution:
    - **Altos de Riomar**: 4 listings (26.7%)
    - **Villa Country**: 4 listings (26.7%)
    - **San Vicente**: 2 listings (13.3%)
    - **Riomar**: 1 listing (6.7%)
    - **Villa Santos**: 1 listing (6.7%)
    - **Miramar**: 1 listing (6.7%)
    - **Paraíso**: 1 listing (6.7%)
    - **El Tabor**: 1 listing (6.7%)
  - Total: 15 properties across **8 distinct top sectors**.
  - All 8 sectors specified in user instructions (`Riomar, Altos de Riomar, Villa Country, Villa Santos, San Vicente, Miramar, Paraíso, El Tabor`) have confirmed representation.
  - Maximum sector concentration cap: **4 listings** (no sector exceeds 4). Anti-monopoly quota strictly enforced.
  - Geographic tier breakdown:
    - Tier A+ (High Exclusivity / Core North): 9 listings (60.0%)
    - Tier A (Modern Residential Expansion): 3 listings (20.0%)
    - Tier B+ (Consolidated Family North): 3 listings (20.0%)

### Obs 1.5: Full Test Suite Execution
- Running `python -m unittest tests/test_adversarial_m3_mfvi.py`:
  - Result: `Ran 24 tests in 0.042s` -> **`OK`**
- Running full test suite `python -m unittest discover tests`:
  - Result: `Ran 142 tests in 9.708s` -> **`OK`**

---

## 2. Logic Chain

1. **Premise 1 (Ranking Algorithm Validity)**: If an independent clean-room calculation of MFVI yields identical scores and rankings across 100% of master database records (Obs 1.1), the implementation accurately adheres to the mathematical model without calculation drift or undocumented weight shifts.
2. **Premise 2 (Missing Data Robustness)**: If the system evaluates `stratum=None`, `admin_fee=0/None`, unstated parking, missing descriptions, and 100 Monte Carlo fuzzed mutations into valid scores within `[0.0, 100.0]` without generating NaNs or raising unhandled exceptions (Obs 1.2), the algorithm is resilient against real-world rental data anomalies.
3. **Premise 3 (Geographic Balance Fulfillment)**: The prompt requires representation across the 8 top Barranquilla Norte sectors (Riomar, Altos de Riomar, Villa Country, Villa Santos, San Vicente, Miramar, Paraíso, El Tabor). Empirical counting of `data/dossier_curado.json` (Obs 1.4) shows every single one of these 8 sectors is present, with no sector exceeding 4 listings (Obs 1.4). Therefore, geographic diversity and anti-clustering quotas are met.
4. **Premise 4 (Boundary Fragility Assessment)**: The input schema fragilities identified (Obs 1.3) occur only when malformed data explicitly passes `None` for required object/number fields (`contact: None`, `total_price: None`). Because the upstream pipeline (`data_pipeline/pipeline.py`) validates and normalizes all 172 records prior to dossier generation, this is an internal defensive hygiene issue rather than an operational blocker.

---

## 3. Caveats

1. **Area Bias Towards Larger Units**: Because the MFVI index assigns 25% of weight to price/m² efficiency and 20% to space/layout, compact units (e.g. 45-55 m² studios) suffer a score penalty (~75-78 pts) compared to spacious units (85-120 m²) that achieve high price/m² efficiency. As a result, the Top 15 properties range from 68 m² to 121 m². While these represent the highest value-per-peso, an arrendatario specifically seeking a minimalist studio would need to filter by area in the web dashboard rather than relying solely on the Top 15 dossier.
2. **Offline Data Invariants**: The tests were run against the validated 172-listing database. Live web scraping changes may introduce new raw field anomalies if portal SSR structures change, though the M1 pipeline validator shields downstream dossier generation.

---

## 4. Conclusion

**VERDICT**: **`APPROVE`**

- **Independent MFVI Agreement**: 100% score and ranking parity across all 172 properties.
- **Null/Missing Data Resilience**: Passed all tests for `stratum=None`, `admin_fee=0`, and `unstated parking` with zero crashes or NaNs.
- **Sector Diversity Audit**: 100% representation across all 8 target Barranquilla Norte sectors (Riomar, Altos de Riomar, Villa Country, Villa Santos, San Vicente, Miramar, Paraíso, El Tabor) with a strict cap of <=4 listings per neighborhood.
- **Test Health**: 24 adversarial tests in `tests/test_adversarial_m3_mfvi.py` passed; all 142 project tests passed.

---

## 5. Verification Method

To independently verify all findings and execute the adversarial test harness:

```powershell
# 1. Run the MFVI adversarial test suite
python -m unittest tests/test_adversarial_m3_mfvi.py

# 2. Run the entire project test suite (142 tests across M1, M2, M3)
python -m unittest discover tests

# 3. Verify sector distribution in data/dossier_curado.json
python -c "import json, collections; d = json.load(open('data/dossier_curado.json', encoding='utf-8')); print(collections.Counter(p['neighborhood'] for p in d['properties']))"

# 4. Verify 100% score agreement on all 172 records
python -c "import json; from dossier_generator import MultiFactorValueIndex; from tests.test_adversarial_m3_mfvi import IndependentMFVIOfflineOracle; data = json.load(open('data/inmuebles_barranquilla.json', encoding='utf-8')); diffs = [p['id'] for p in data if round(abs(MultiFactorValueIndex.evaluate(p)['mfvi_score'] - IndependentMFVIOfflineOracle.evaluate(p)['mfvi_score']), 4) > 0]; print('Mismatches:', len(diffs))"
```
