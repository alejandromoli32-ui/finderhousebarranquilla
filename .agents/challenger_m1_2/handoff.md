# Adversarial Challenge Report — Milestone 1: Deduplication & Geographic Integrity

**Agent**: `challenger_m1_2`  
**Parent**: `orchestrator_1` (Conversation ID: `78e1bffd-c00b-4edf-9b66-26fc5574a726`)  
**Timestamp**: 2026-09-13T22:15:30Z  
**Verdict**: **`REJECT`** (Remediation required on geographic filtering and schema attribute sanitization)

---

## Challenge Summary

- **Overall Risk Assessment**: **HIGH**
- **Core Strengths**: 
  - The Deduplication Engine (`data_pipeline/deduplicator.py`) is exceptionally robust: 100% pass rate on fuzzy duplicate clustering ($50.000 COP price delta, 1 m² area delta, street matches, transitive Union-Find clustering, unmasked contact attribute merging, image union).
  - Non-duplicate isolation is airtight: distinct bedroom counts, price deltas > $150k COP, conflicting known building tokens, different neighborhoods, and area differences > 5 m² without building tokens are strictly isolated.
  - JSON (`inmuebles_barranquilla.json`) vs CSV (`inmuebles_barranquilla.csv`) parity is a perfect 1:1 match across all 173 rows, all 25 columns, and includes the valid Microsoft Excel UTF-8 BOM (`\xef\xbb\xbf`).
  - Price ceiling ($2.500.000 COP) and price arithmetic (`total_price == canon + admin_fee`) hold for 100% of the 173 records.
- **Critical Vulnerabilities Requiring Fix**:
  1. **Geographic Leakage (External Municipality)**: Listing `FR-191933365` (neighborhood: "Puerto colombia", title: "Apartamento en Arriendo en Puerto colombia") leaked into `data/inmuebles_barranquilla.json`.
  2. **Filter Bypass Flaw in `data_pipeline/pipeline.py` (lines 156-159)**: The condition `if not (is_allowed_barrio or is_norte_zone):` allows any listing marked with `zone: "Noroccidente"` to bypass `ALLOWED_BARRIOS`, completely rendering the neighborhood whitelist ineffective whenever zone is "Noroccidente" or "Norte".
  3. **Interface Contract Violations in `data/inmuebles_barranquilla.json`**:
     - `MERGED-21392-M7032477-194143777`: `zone = "Otros"`, violating `PROJECT.md` line 72 contract (`'zone': string ('Norte' | 'Noroccidente')`).
     - `FR-192126512`: `bedrooms = -1` (negative room count), violating `PROJECT.md` line 75.
     - `FR-193957120`: `stratum = 110` (out of range socioeconomic stratum), violating `PROJECT.md` line 78 contract (`'stratum': number (int 1-6)`).

---

## 1. Observation

### Obs 1. Deduplication Engine Fuzzy & Hard Gates Execution
In test file `tests/test_adversarial_dedup_geo.py`:
- Executed `TestAdversarialDeduplicationSyntheticDuplicates`:
  - `test_fuzzy_price_delta_50k_and_area_delta_1m2_merged`: Listing A ($2.150.000 COP, 65 m², canon $2.0M, admin $150k) and Listing B ($2.100.000 COP, 66 m², admin $0) generated `sim = 0.875 >= 0.70`. Output: exactly 1 merged listing with tenant-optimal total price `$2.100.000 COP`, preserved admin fee `$150.000 COP`, canon `$1.950.000 COP`, combined images count = 2, unmasked phone = `3007771690`, WhatsApp = `573007771690`. (PASS)
  - `test_fuzzy_price_delta_100k_and_area_delta_3m2_merged`: $100.000 COP delta, 3 m² delta with street token match ("Cra 51 # 96-30"). Output: 1 merged listing. (PASS)
  - `test_transitive_clustering_union_find`: Listings A ~ B and B ~ C merged into 1 single cluster of 3 with `merged_duplicates = 2`. (PASS)
- Executed `TestAdversarialDeduplicationNonDuplicates`:
  - `test_different_bedrooms_in_same_building_never_merge`: 2 hab vs 3 hab in same building -> `sim = 0.0`, output: 2 separate listings. (PASS)
  - `test_price_delta_exceeding_150k_never_merge`: $1.8M vs $2.1M (delta $300k) -> `sim = 0.0`, output: 2 separate listings. (PASS)
  - `test_price_delta_boundary_150001_rejected_150000_allowed`: Delta $150.000 COP yields `sim >= 0.70`, whereas delta $150.001 COP yields `sim = 0.0`. (PASS)
  - `test_different_bathrooms_difference_gte_2_never_merge`: 1 bath vs 3 bath -> `sim = 0.0`, output: 2 separate listings. (PASS)
  - `test_conflicting_building_names_never_merge`: "Edificio Sorrento" vs "Edificio Torino" -> `sim = 0.0`, output: 2 separate listings. (PASS)
  - `test_different_neighborhoods_never_merge`: "Miramar" vs "El Golf" -> `sim = 0.0`, output: 2 separate listings. (PASS)
  - `test_large_area_difference_without_token_never_merge`: 50 m² vs 65 m² in same barrio without building token -> `sim = 0.0`, output: 2 separate listings. (PASS)

### Obs 2. Geographic Integrity and Leakage Scan
Inspection of `data/inmuebles_barranquilla.json` (173 records):
- **Southern Barranquilla Leakage**: 0 listings found in Rebolo, La Chinita, El Bosque, Simón Bolívar, San Roque, Chiquinquirá, Montes, etc. (PASS)
- **External Municipalities Leakage**:
  - Listing `FR-191933365`:
    ```json
    {
      "id": "FR-191933365",
      "portal": "Finca Raiz",
      "title": "Apartamento en  Arriendo en Puerto colombia",
      "neighborhood": "Puerto colombia",
      "zone": "Noroccidente",
      "address": "Carrera 22 # 1 E - 127 Apto 202 Torre 2,Conjunto Residencial El Manglar",
      "url": "https://www.fincaraiz.com.co/apartamento-en-arriendo-en-puerto-colombia/191933365",
      "total_price": 1500000
    }
    ```
    Observed verbatim: `neighborhood: "Puerto colombia"`, `title: "Apartamento en  Arriendo en Puerto colombia"`, `url: ".../arriendo-en-puerto-colombia/..."`. (LEAK VIOLATION)
  - In `data_pipeline/pipeline.py` (lines 152-160):
    ```python
    barrio = prop.get("neighborhood", "")
    norm_barrio = normalize_neighborhood(barrio)
    zone = str(prop.get("zone", "")).lower()

    is_allowed_barrio = norm_barrio in ALLOWED_BARRIOS
    is_norte_zone = any(z in zone for z in ["norte", "noroccidente", "riomar", "historico"])

    if not (is_allowed_barrio or is_norte_zone):
        return False, f"Neighborhood '{barrio}' (zone '{zone}') is outside Barranquilla Norte target sector"
    ```
    Because `is_norte_zone` evaluates to `True` for any record tagged by the scraper with `zone: "Noroccidente"`, `is_allowed_barrio or is_norte_zone` evaluates to `True`, allowing non-whitelisted neighborhoods (such as `"Puerto colombia"`) to pass validation unconditionally.

### Obs 3. Physical Invariants & Schema Contract Violations
- In `data/inmuebles_barranquilla.json`:
  1. `FR-192126512`: `"bedrooms": -1`. In `data_pipeline/pipeline.py` line 174, `prop["bedrooms"] = int(prop.get("bedrooms", 0) or 0)` fails to assert `bedrooms >= 1`.
  2. `FR-193957120`: `"stratum": 110`. In `data_pipeline/pipeline.py` line 189, `prop["stratum"] = int(prop.get("stratum", 0) or 4)` fails to assert `1 <= stratum <= 6`.
  3. `MERGED-21392-M7032477-194143777`: `"zone": "Otros"`. In `PROJECT.md` line 72, the contract specifies: `"zone": "string ('Norte' | 'Noroccidente')"`.

### Obs 4. JSON vs CSV 1:1 Parity
- Verified via `TestJsonVsCsvExactParity`:
  - `data/inmuebles_barranquilla.csv` starts with UTF-8 BOM bytes `b'\xef\xbb\xbf'`.
  - CSV contains exactly 173 rows, matching the 173 JSON objects.
  - IDs appear in identical sequential order from row 0 to row 172.
  - Field values match verbatim across all 25 columns: `id`, `portal`, `title`, `property_type`, `canon`, `admin_fee`, `total_price`, `price_per_m2`, `neighborhood`, `zone`, `address`, `area_m2`, `bedrooms`, `bathrooms`, `parking`, `stratum`, `url`, `contact_phone`, `contact_whatsapp`, `contact_agency`, `contact_agent_name`, `images_count`, `main_image`, `verified`, `description`.
  - Calculated `price_per_m2` formula matches `round(total_price / area_m2)`. (PASS)

---

## 2. Logic Chain

1. **Premise 1**: ORIGINAL_REQUEST §R1 and Acceptance Criteria stipulate that the database must strictly contain rental properties in Barranquilla within the target sector (Norte/Noroccidente) and exclude external municipalities or southern sectors.
2. **Premise 2**: Observation 2 establishes that `FR-191933365` is located in Puerto Colombia municipality (`neighborhood: "Puerto colombia"`, `url: ".../puerto-colombia/191933365"`, `address: "...El Manglar"`).
3. **Premise 3**: Observation 2 identifies the root cause in `data_pipeline/pipeline.py`: the disjunction `(is_allowed_barrio or is_norte_zone)` nullifies the whitelist `ALLOWED_BARRIOS` for any record where `zone` contains `"noroccidente"`, allowing external municipalities to leak into production data.
4. **Premise 4**: PROJECT.md §Interface Contracts defines valid ranges: `bedrooms >= 1`, `stratum` in `1..6`, and `zone` in `['Norte', 'Noroccidente']`.
5. **Premise 5**: Observation 3 demonstrates that `FR-192126512` contains `bedrooms: -1`, `FR-193957120` contains `stratum: 110`, and `MERGED-21392-M7032477-194143777` contains `zone: "Otros"`.
6. **Conclusion**: While the Deduplication Engine and CSV serializer meet high engineering standards, the pipeline's geographic validation logic and input sanitization allowed an external municipality listing and three contract-violating records into the production dataset. Therefore, the milestone must be marked **`REJECT`** until these defects are remediated.

---

## 3. Challenges & Failure Modes

### Challenge 1: Permissive Geography Gate (`or is_norte_zone`)
- **Assumption Challenged**: Believing that checking `is_norte_zone` is a safe fallback for unclassified neighborhoods.
- **Attack Scenario**: Scrapers on Finca Raíz or Metrocuadrado frequently tag listings in Puerto Colombia, Sabanilla, or Salgar with zone "Noroccidente". Because of the `or`, these listings bypass `ALLOWED_BARRIOS`.
- **Blast Radius**: Dirty geographic data polluting the tracker with out-of-town properties.
- **Mitigation**: Tighten `data_pipeline/pipeline.py` line 159:
  ```python
  # Reject explicit external municipalities
  norm_barrio = normalize_neighborhood(barrio)
  DISALLOWED_KEYWORDS = {"puerto_colombia", "puerto colombia", "soledad", "malambo", "galapa", "abajo"}
  if norm_barrio in DISALLOWED_KEYWORDS or "puerto colombia" in str(prop.get("url", "")).lower():
      return False, f"Neighborhood '{barrio}' is an external municipality or out of bounds"

  is_allowed_barrio = norm_barrio in ALLOWED_BARRIOS
  if not is_allowed_barrio:
      # If not in whitelist, require both 'desconocido' AND zone in Norte/Noroccidente
      if norm_barrio == "desconocido" and any(z in zone for z in ["norte", "noroccidente", "riomar"]):
          pass
      else:
          return False, f"Neighborhood '{barrio}' not in target sector whitelist"
  ```

### Challenge 2: Missing Clamping on Physical Fields
- **Assumption Challenged**: Believing portal data contains valid physical dimensions and strata.
- **Attack Scenario**: Scrapers encounter default sentinel values like `-1` for unknown bedrooms, or input typos like `110` for stratum.
- **Blast Radius**: Frontend filtering sliders break or display nonsensical filters (e.g. "-1 Habitación", "Estrato 110").
- **Mitigation**: Add clamping in `data_pipeline/pipeline.py`:
  ```python
  prop["bedrooms"] = max(1, int(prop.get("bedrooms", 1) or 1))
  raw_stratum = int(prop.get("stratum", 4) or 4)
  prop["stratum"] = raw_stratum if 1 <= raw_stratum <= 6 else 4
  ```

### Challenge 3: Invariant Violation in Deduplicated Zone
- **Assumption Challenged**: Merged records will always have a valid zone.
- **Attack Scenario**: A primary listing has `zone: "Otros"` (e.g. from Metrocuadrado), which gets propagated into the merged output.
- **Blast Radius**: Downstream zone filters in `app.js` fail to categorize the listing.
- **Mitigation**: In `data_pipeline/deduplicator.py` line 334, enforce:
  ```python
  clean_zone = primary.get("zone", "Norte")
  if clean_zone not in ["Norte", "Noroccidente"]:
      clean_zone = "Noroccidente" if "noroccidente" in clean_zone.lower() else "Norte"
  ```

---

## 4. Stress Test Results

| Test Scenario | Module | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| Synthetic Duplicates: $50k delta, 1 m² delta | Deduplicator | Merged into 1 record, optimal price $2.1M | Merged, total=$2.1M, admin=$150k, canon=$1.95M | **PASS** |
| Synthetic Duplicates: $100k delta, 3 m² delta | Deduplicator | Merged into 1 record, optimal price $2.4M | Merged, total=$2.4M, admin=$400k, canon=$2.0M | **PASS** |
| Transitive Duplicate Clustering (A~B, B~C) | Deduplicator | Single cluster of 3, merged_count=2 | 1 record, merged_duplicates=2 | **PASS** |
| Non-Duplicates: Different bedrooms (2 vs 3) | Deduplicator | 2 distinct records, sim=0.0 | 2 distinct records, sim=0.0 | **PASS** |
| Non-Duplicates: Price delta > $150k COP | Deduplicator | 2 distinct records, sim=0.0 | 2 distinct records, sim=0.0 | **PASS** |
| Non-Duplicates: Exact price boundary ($150k vs $150.001) | Deduplicator | $150k merges, $150.001 rejected | $150k sim>=0.70, $150.001 sim=0.0 | **PASS** |
| Non-Duplicates: Conflicting buildings (Sorrento vs Torino) | Deduplicator | 2 distinct records, sim=0.0 | 2 distinct records, sim=0.0 | **PASS** |
| Non-Duplicates: Area diff > 5 m² without token | Deduplicator | 2 distinct records, sim=0.0 | 2 distinct records, sim=0.0 | **PASS** |
| Southern Barranquilla zero leakage | Geography | 0 southern records | 0 southern records found | **PASS** |
| Price ceiling <= $2.5M & math parity (173 records) | Finance | 100% compliant | 173/173 compliant (0 violations) | **PASS** |
| External Municipalities Leakage Audit | Geography | 0 external municipality records | 1 leaked record (`FR-191933365` Puerto Colombia) | **FAIL** |
| Zone contract compliance (`Norte` \| `Noroccidente`) | Schema | 0 invalid zones | 1 invalid zone (`MERGED-...` zone='Otros') | **FAIL** |
| Positive integer bedrooms (`bedrooms >= 1`) | Physical | 0 negative bedrooms | 1 invalid record (`FR-192126512` bedrooms=-1) | **FAIL** |
| Socioeconomic stratum range (`stratum in 1..6`) | Physical | 0 out-of-range strata | 1 invalid record (`FR-193957120` stratum=110) | **FAIL** |
| JSON vs CSV 1:1 row count & order match | Serialization | Exactly 173 rows matching IDs | 173 rows matched in exact order | **PASS** |
| CSV UTF-8 BOM byte presence | Serialization | `\xef\xbb\xbf` at index 0 | Verified `\xef\xbb\xbf` present | **PASS** |
| Field-by-field parity across all 25 CSV columns | Serialization | Identical values | Identical values across all 25 columns | **PASS** |

---

## 5. Caveats

- **Offline Dataset Scope**: Scrapers were tested against the cached/fallback dataset (`data_pipeline/fallback_data.json`) containing 318 raw listings. Live scraper runs against Metrocuadrado and Finca Raíz will depend on current portal CAPTCHAs, though the offline fallback mechanism functioned properly during pipeline execution.
- **Ciudad Mallorquín Geographic Classification**: Ciudad Mallorquín is physically located in Puerto Colombia's municipal territory on the urban border of Barranquilla. However, because `PROJECT.md` line 6 explicitly names it as an approved target sector, listings in Ciudad Mallorquín were evaluated as valid project scope.

---

## 6. Conclusion & Action Plan

**Final Verdict**: **`REJECT`**

### Required Action Items for Developer:
1. **Fix `data_pipeline/pipeline.py` (line 159)**: Disallow `puerto colombia`, `soledad`, `malambo`, `galapa`, `abajo`. Disallow `or is_norte_zone` from bypassing `ALLOWED_BARRIOS`.
2. **Fix numerical sanitization in `data_pipeline/pipeline.py` (lines 174-192)**:
   - Ensure `bedrooms = max(1, ...)`
   - Ensure `stratum = val if 1 <= val <= 6 else 4`
3. **Fix zone sanitization in `data_pipeline/deduplicator.py` (line 334)**: Ensure `zone` is strictly normalized to `"Norte"` or `"Noroccidente"`.
4. **Re-execute pipeline**: `python -m data_pipeline.pipeline --offline` to refresh `data/inmuebles_barranquilla.json` and `data/inmuebles_barranquilla.csv`.
5. **Re-run test suite**: Verify that all 21 tests in `tests/test_adversarial_dedup_geo.py` pass with 0 failures.

---

## 7. Verification Method

To independently reproduce and verify these findings:
```powershell
# Run the empirical adversarial test suite
python -m unittest tests/test_adversarial_dedup_geo.py -v
```
Expected output: 17 PASS, 4 FAIL (highlighting the exact IDs `FR-191933365`, `FR-192126512`, `FR-193957120`, and `MERGED-21392-M7032477-194143777`).
