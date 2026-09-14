# Handoff Report: Interface Contract Zone Invariant & Adversarial Test Verification

**Agent**: `explorer_m1_retry_3`  
**Parent**: `orchestrator_1` (Conversation ID: `78e1bffd-c00b-4edf-9b66-26fc5574a726`)  
**Timestamp**: 2026-09-13T22:20:00Z  
**Type**: Hard Handoff (Investigation Complete)  
**Detailed Findings File**: `c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/explorer_m1_retry_3/analysis.md`

---

## 1. Observation

### Obs 1. Listing `MERGED-21392-M7032477-194143777` Zone Violation
- In `data/inmuebles_barranquilla.json` (lines 6718–6726) and `data/inmuebles_barranquilla.csv` (line 110):
  ```json
  {
    "id": "MERGED-21392-M7032477-194143777",
    "portal": "Metrocuadrado + Finca Raiz",
    "title": "Apartamento en Arriendo en Ciudad Mallorquin, Puerto colombia",
    "neighborhood": "Ciudad Mallorquin",
    "zone": "Otros"
  }
  ```
  `zone` is `"Otros"`.
- In `PROJECT.md § Interface Contracts` (line 72):
  ```json
  "zone": "string ('Norte' | 'Noroccidente')",
  ```
  This is a direct interface contract violation.
- In `data_pipeline/fallback_data.json`:
  - Constituent listing `MQ-21392-M7032477` (lines 3473–3481) has `"neighborhood": "Ciudad Mallorquin"`, `"zone": "Otros"`.
  - Constituent listing `FR-194143777` (lines 11187–11195) has `"neighborhood": "Ciudad Mallorquin"`, `"zone": "Noroccidente"`.
- In `data_pipeline/deduplicator.py` (line 334):
  `"zone": primary.get("zone", "Norte")` selected `MQ-21392-M7032477` as `primary` and propagated `"Otros"` directly into production data.
- In `data_pipeline/extractors/metrocuadrado.py` (lines 204–207):
  ```python
  zona_obj = itm.get("mzona") or {}
  zone_name = zona_obj.get("nombre") if isinstance(zona_obj, dict) else None
  if not zone_name:
      zone_name = default_zone
  ```
  Non-standard zone `"Otros"` was returned by Metrocuadrado and bypassed `default_zone`.
- In `data_pipeline/fallback_data.json`, 10 listings have `zone: "Otros"` and 2 have `zone: "Villa Campestre"` (total 12 non-standard zones).

### Obs 2. Execution of `tests/test_adversarial_dedup_geo.py`
Command executed:
```powershell
python -m unittest tests/test_adversarial_dedup_geo.py
```
Verbatim result:
```
Ran 21 tests in 0.032s
FAILED (failures=4)

[LEAK DETECTION] Puerto Colombia municipality listings count: 1 (IDs: ['FR-191933365'])
[PHYSICAL AUDIT] Negative/zero bedroom listings: [('FR-192126512', -1)]
[PHYSICAL AUDIT] Out of range stratum listings: [('FR-193957120', 110)]
[SCHEMA AUDIT] Invalid zone listings count: 1: [('MERGED-21392-M7032477-194143777', 'Otros')]
```
17 tests pass; 4 fail:
1. `test_adversarial_leakage_audit_puerto_colombia`: detects `FR-191933365` (leak).
2. `test_bedrooms_valid_positive_count`: detects `FR-192126512` (bedrooms = -1).
3. `test_stratum_in_socioeconomic_range_1_to_6`: detects `FR-193957120` (stratum = 110).
4. `test_zone_interface_contract_conformance`: detects `MERGED-21392-M7032477-194143777` (zone = "Otros").

### Obs 3. Suite Inventory and Record Count Hardcoding Flaw
- `tests/test_adversarial_dedup_geo.py` contains exactly 21 test methods across 4 classes:
  - `TestAdversarialDeduplicationSyntheticDuplicates` (3 tests: lines 34, 98, 147)
  - `TestAdversarialDeduplicationNonDuplicates` (7 tests: lines 179, 200, 219, 243, 258, 275, 290)
  - `TestGeographicIntegrityEmpirical` (7 tests: lines 314, 318, 332, 351, 370, 387, 403)
  - `TestJsonVsCsvExactParity` (4 tests: lines 438, 442, 447, 454)
- Line 315 (`test_exact_record_count_is_173`): `self.assertEqual(len(self.listings), 173)`.
- Line 445 (`test_exact_row_count_match`): `self.assertEqual(len(self.json_data), 173)`.
- `FR-191933365` is a standalone, unmerged listing. Purging `FR-191933365` drops inventory from 173 to **172**.
- Empirical simulation confirms that if `FR-191933365` is purged without updating lines 315 and 445, tests 11 and 19 fail with `AssertionError: 172 != 173`.

### Obs 4. Whitelist Bypass vs Over-Pruning Risk
- In `data_pipeline/pipeline.py` (lines 156–159):
  `if not (is_allowed_barrio or is_norte_zone):`
- In `data_pipeline/fallback_data.json`, 24 listings use minor spelling variations:
  - 7 `Ciudad de Mallorquin`
  - 3 `El Porvenir`
  - 3 `Betania`
  - 3 `Conjunto residencial villa campestre`
  - 2 `Rio Alto`
  - 2 `Ciudad Mallorquin Zona Urbana`
  - 1 `Altos del limon`
  - 1 `Altos de San Vicente`
  - 1 `Golf Alto Prado`
  - 1 `El Paraiso`
- A naive `norm_barrio in ALLOWED_BARRIOS` filter without updating `NEIGHBORHOOD_SYNONYMS` drops these 24 valid listings, collapsing verified inventory to 149.

---

## 5-Component Logic Chain

1. **Step 1 (Root Cause of Zone Invariant)**: Observation 1 establishes that Metrocuadrado returns raw string `"Otros"` in `mzona.nombre`. Because `extractors/metrocuadrado.py` does not constrain `zone_name` to `('Norte', 'Noroccidente')`, `"Otros"` enters the pipeline. Because `pipeline.py` lacks a schema assertion on `zone`, and `deduplicator.py` copies `primary.get("zone")`, `"Otros"` leaked into `MERGED-21392-M7032477-194143777`.
2. **Step 2 (Deterministic Mapping Formulation)**: `Ciudad Mallorquin` is part of the northwestern expansion corridor adjacent to Riomar and Puerto Colombia border. In `DEFAULT_NEIGHBORHOOD_SLUGS` and `fincaraiz.py`, `Ciudad Mallorquin` is assigned `"Noroccidente"`. Finca Raiz constituent `FR-194143777` has `"Noroccidente"`. By mapping every admitted neighborhood through an authoritative matrix (`BARRIO_TO_ZONE`), `Ciudad Mallorquin` deterministically resolves to `"Noroccidente"`.
3. **Step 3 (Adversarial Suite Analysis)**: Observation 2 demonstrates that the deduplication engine (classes 1 and 2, 10 tests) passes with 100% precision. The 4 failures are strictly confined to data hygiene in class 3: external municipality leak (`FR-191933365`), unconstrained bedrooms (`FR-192126512`), unconstrained stratum (`FR-193957120`), and unconstrained zone (`MERGED-21392-M7032477-194143777`).
4. **Step 4 (Test Conflict Resolution)**: Observation 3 proves that purging `FR-191933365` reduces clean inventory to 172. Hardcoding 173 in tests 11 and 19 is an internal contradiction in `challenger_m1_2`'s suite. Setting expected inventory to 172 resolves the conflict cleanly.
5. **Step 5 (Inventory Preservation)**: Observation 4 proves that fixing the geographic filter requires adding the 11 spelling variations to `NEIGHBORHOOD_SYNONYMS` so that legitimate Northern listings in El Porvenir, Betania, and Ciudad de Mallorquin are not dropped.

---

## 3. Caveats

1. **Ciudad Mallorquín Territory vs Project Scope**: Ciudad Mallorquín is administratively located in Puerto Colombia's municipal boundary. However, `PROJECT.md` line 6 and `challenger_m1_2/handoff.md` lines 178–179 explicitly define Ciudad Mallorquín as within project scope. Finca Raíz URLs for Ciudad Mallorquín contain `/ciudad-mallorquin-puerto-colombia/`. Any URL filter must exclude `ciudad-mallorquin` before matching `puerto-colombia`.
2. **Read-Only Scope**: In accordance with explorer constraints, no production files were modified during this investigation. All proposed changes are documented as exact diffs in `analysis.md`.
3. **Live Portal CAPTCHA Invariance**: Scraper execution was verified against offline fallback datasets. Live scraper runs remain subject to portal CAPTCHA and rate limits.

---

## 4. Conclusion

1. **Deterministic Zone Mapping**: `MERGED-21392-M7032477-194143777` must be deterministically mapped to `zone: "Noroccidente"`. Implementing defense-in-depth across `metrocuadrado.py` (line 204), `pipeline.py` (line 151), and `deduplicator.py` (line 334) guarantees `zone in ("Norte", "Noroccidente")` across 100% of admitted records.
2. **Verification Criteria for All 21 Tests**:
   - Class 1 (Synthetic Duplicates, 3 tests): Pass unconditionally. Require similarity >= 0.70, single record output, tenant-optimal price arithmetic, unmasked contact, image union.
   - Class 2 (Non-Duplicates, 7 tests): Pass unconditionally. Require similarity == 0.0 and two isolated records for bedroom difference, price delta > $150k, price delta boundary $150.001, bathroom delta >= 2, conflicting building tokens, distinct neighborhoods, and area delta > 5 m².
   - Class 3 (Geographic Integrity, 7 tests):
     - Test 11: Expect 172 records post-purge.
     - Test 12: 100% compliance with price ceiling <= $2.5M and canon + admin == total.
     - Test 13: 0 matches for 17 southern tokens.
     - Test 14: 0 Puerto Colombia leaks post-rejection of `FR-191933365`.
     - Test 15: 0 invalid zones post-mapping of `MERGED-21392-M7032477-194143777` to `"Noroccidente"`.
     - Test 16: 0 negative/zero bedrooms post-clamping (`max(1, raw_beds)`).
     - Test 17: 0 out-of-range strata post-clamping (`1 <= stratum <= 6`).
   - Class 4 (JSON vs CSV Parity, 4 tests):
     - Test 18: CSV starts with `\xef\xbb\xbf` UTF-8 BOM.
     - Test 19: `len(json) == len(csv) == 172`.
     - Test 20: 1:1 identical ID sequence from index 0 to 171.
     - Test 21: Full field equality across all 25 CSV columns.

---

## 5. Verification Method

To independently verify after the developer applies the proposed changes:
```powershell
# 1. Re-run pipeline offline to generate clean datasets
python -m data_pipeline.pipeline --offline

# 2. Run the 21-test empirical adversarial suite
python -m unittest tests/test_adversarial_dedup_geo.py -v
```
Expected post-remediation result:
`Ran 21 tests in 0.035s — OK (21 passed, 0 failures, 0 errors)`.
