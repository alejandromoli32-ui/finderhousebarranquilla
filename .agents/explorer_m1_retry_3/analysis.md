# Detailed Analysis: Interface Contract Zone Invariant & Adversarial Test Verification

**Agent**: `explorer_m1_retry_3`  
**Parent**: `orchestrator_1` (Conversation ID: `78e1bffd-c00b-4edf-9b66-26fc5574a726`)  
**Workspace**: `c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR`  
**Date**: 2026-09-13  
**Status**: COMPLETE (Read-Only Investigation)

---

## 1. Executive Summary

This investigation resolves two critical quality and architectural mandates for Milestone 1:
1. **Interface Contract Zone Invariant**: `PROJECT.md § Interface Contracts` establishes that every listing admitted to `data/inmuebles_barranquilla.json` and `data/inmuebles_barranquilla.csv` must have a `zone` attribute satisfying `zone: string ('Norte' | 'Noroccidente')`. In the current database, listing `MERGED-21392-M7032477-194143777` violates this invariant with `zone: "Otros"`. This analysis tracks the origin of `"Otros"` through the Metrocuadrado SSR API, across the pipeline ingestion filter, and through cluster merging in `deduplicator.py`. We formulate an authoritative, deterministic mapping so that 100% of admitted properties are mapped to either `"Norte"` or `"Noroccidente"`.
2. **Verification Criteria for All 21 Adversarial Unit Tests**: We conducted an exhaustive code audit of `tests/test_adversarial_dedup_geo.py` created by `challenger_m1_2`. We formulated explicit, reproducible verification criteria for all 21 unit tests across 4 test classes. Furthermore, we uncovered a critical test-suite flaw: two tests hardcode an inventory count of `173`, which directly contradicts the requirement to purge the external municipality listing `FR-191933365` (which reduces clean inventory to `172`). We provide the mathematical and algorithmic resolution for this count discrepancy.

---

## 2. Root Cause Analysis: Listing `MERGED-21392-M7032477-194143777` (`zone: "Otros"`)

### 2.1 Component Trace
1. **Origin in Raw Scraper Data**:
   - `MERGED-21392-M7032477-194143777` is a cross-portal duplicate formed by two raw listings:
     - `MQ-21392-M7032477` (from Metrocuadrado):
       - Title: `"Apartamento en Arriendo, CIUDAD MALLORQUIN, Barranquilla"`
       - Neighborhood: `"Ciudad Mallorquin"`
       - Raw `mzona` field: `{"nombre": "Otros"}`
       - Extractor output: `"zone": "Otros"`
     - `FR-194143777` (from Finca Raíz):
       - Title: `"Apartamento en Arriendo en Ciudad Mallorquin, Puerto colombia"`
       - Neighborhood: `"Ciudad Mallorquin"`
       - Extractor output: `"zone": "Noroccidente"`
2. **Defect in `data_pipeline/extractors/metrocuadrado.py` (lines 204–207)**:
   ```python
   zona_obj = itm.get("mzona") or {}
   zone_name = zona_obj.get("nombre") if isinstance(zona_obj, dict) else None
   if not zone_name:
       zone_name = default_zone
   ```
   *Observation*: When Metrocuadrado returns `{"nombre": "Otros"}` or `{"nombre": "Villa Campestre"}`, `zone_name` is non-empty, so it completely ignores `default_zone` (which was set to `"Noroccidente"` for `ciudad-mallorquin` in `DEFAULT_NEIGHBORHOOD_SLUGS`).
3. **Defect in `data_pipeline/pipeline.py` (lines 151–160)**:
   ```python
   barrio = prop.get("neighborhood", "")
   norm_barrio = normalize_neighborhood(barrio)
   zone = str(prop.get("zone", "")).lower()

   is_allowed_barrio = norm_barrio in ALLOWED_BARRIOS
   is_norte_zone = any(z in zone for z in ["norte", "noroccidente", "riomar", "historico"])

   if not (is_allowed_barrio or is_norte_zone):
       return False, f"Neighborhood '{barrio}' (zone '{zone}') is outside Barranquilla Norte target sector"
   ```
   *Observation*: Because `norm_barrio` (`"ciudad_mallorquin"`) was in `ALLOWED_BARRIOS`, `is_allowed_barrio` was `True`. The pipeline allowed `MQ-21392-M7032477` to pass validation without asserting or enforcing that `prop["zone"] in ["Norte", "Noroccidente"]`.
4. **Defect in `data_pipeline/deduplicator.py` (line 334)**:
   ```python
   "zone": primary.get("zone", "Norte"),
   ```
   *Observation*: In the cluster `{MQ-21392-M7032477, FR-194143777}`, `MQ-21392-M7032477` was elected as `primary` due to having an unmasked phone (`"3126600425"` vs `"+5731"`). `merge_cluster` blindly copied `primary.get("zone")`, propagating `"Otros"` into `data/inmuebles_barranquilla.json`.

---

## 3. Formulating the Deterministic Zone Mapping

### 3.1 Geographic and Domain Specification
Barranquilla's northern rental market spans two primary administrative localities:
- **Localidad Riomar**: Comprises the northern and northwestern high-growth and residential corridor: Riomar, Altos de Riomar, Villa Santos, Miramar, Buenavista, La Campiña, El Tabor, Andalucía, La Cumbre, Ciudad Jardín, Granadillo, Santa Mónica, Villa Campestre, and Ciudad Mallorquín (urban expansion zone).
- **Localidad Norte-Centro Histórico**: Comprises traditional high-stratum residential and commercial sectors: El Golf, Alto Prado, Villa Country, Bellavista, El Prado, El Limoncito, Paraíso, San Vicente, El Porvenir, Betania, and Alameda del Río.

According to `PROJECT.md § Interface Contracts`:
```json
"zone": "string ('Norte' | 'Noroccidente')"
```
Every listing admitted into the project must deterministically map to one of these two values.

### 3.2 Authoritative Neighborhood-to-Zone Matrix (`BARRIO_TO_ZONE`)

| Normalized Barrio Key (`norm_barrio`) | Target Neighborhood / Synonyms | Locality Sector | Deterministic Zone |
|---|---|---|---|
| `miramar` | Miramar, Horizontes de Miramar | Riomar / Hills | **`Noroccidente`** |
| `riomar` | Riomar, Altos de Riomar, Alto de Riomar | Riomar Central | **`Noroccidente`** |
| `altos_del_limon` | Altos del Limón | Riomar | **`Noroccidente`** |
| `rio_alto` | Río Alto | Riomar | **`Noroccidente`** |
| `villa_santos` | Villa Santos, Santos | Riomar North | **`Noroccidente`** |
| `buenavista` | Buenavista | Riomar | **`Noroccidente`** |
| `ciudad_mallorquin` | Ciudad Mallorquín, Ciudad de Mallorquín | Riomar Expansion | **`Noroccidente`** |
| `la_campina` | La Campiña, Campiña | Riomar West | **`Noroccidente`** |
| `tabor` | El Tabor, Tabor | Riomar West | **`Noroccidente`** |
| `los_alpes` | Los Alpes, Alpes | Riomar / Norte Border | **`Noroccidente`** |
| `andalucia` | Andalucía | Riomar East | **`Noroccidente`** |
| `la_cumbre` | La Cumbre, Cumbre | Riomar West | **`Noroccidente`** |
| `ciudad_jardin` | Ciudad Jardín | Riomar / Norte Border | **`Noroccidente`** |
| `granadillo` | Granadillo | Riomar West | **`Noroccidente`** |
| `santa_monica` | Santa Mónica | Riomar Central | **`Noroccidente`** |
| `villa_campestre` | Villa Campestre, Res. Villa Campestre | Northern Corridor | **`Noroccidente`** |
| `el_golf` | El Golf, Golf, Golf Alto Prado | Norte-Centro Histórico | **`Norte`** |
| `alto_prado` | Alto Prado, Altos del Prado, El Prado, Prado | Norte-Centro Histórico | **`Norte`** |
| `villa_country` | Villa Country, Country | Norte-Centro Histórico | **`Norte`** |
| `villa_carolina` | Villa Carolina, Carolina | Riomar East / Vía 40 | **`Norte`** |
| `el_limoncito` | El Limoncito, Limoncito | Riomar / Norte | **`Norte`** |
| `paraiso` | Paraíso, El Paraíso, Villa Paraíso | Norte-Centro Histórico | **`Norte`** |
| `bellavista` | Bellavista | Norte-Centro Histórico | **`Norte`** |
| `san_vicente` | San Vicente, Altos de San Vicente | Riomar / Norte | **`Norte`** |
| `el_porvenir` | El Porvenir, Porvenir | Norte-Centro Histórico | **`Norte`** |
| `betania` | Betania | Norte-Centro Histórico | **`Norte`** |
| `alameda_del_rio` | Alameda del Río | Circunvalar Norte | **`Norte`** |
| `la_concepcion` | La Concepción | Norte-Centro Histórico | **`Norte`** |

### 3.3 The Deterministic Zone Resolution Algorithm
To ensure defense-in-depth across the entire pipeline, the resolution logic follows this strict order of operations:

```python
BARRIO_TO_ZONE: Dict[str, str] = {
    # Noroccidente Corridor
    "miramar": "Noroccidente",
    "riomar": "Noroccidente",
    "altos_de_riomar": "Noroccidente",
    "altos_del_limon": "Noroccidente",
    "rio_alto": "Noroccidente",
    "villa_santos": "Noroccidente",
    "buenavista": "Noroccidente",
    "ciudad_mallorquin": "Noroccidente",
    "la_campina": "Noroccidente",
    "tabor": "Noroccidente",
    "los_alpes": "Noroccidente",
    "andalucia": "Noroccidente",
    "la_cumbre": "Noroccidente",
    "ciudad_jardin": "Noroccidente",
    "granadillo": "Noroccidente",
    "santa_monica": "Noroccidente",
    "villa_campestre": "Noroccidente",
    
    # Norte Corridor
    "el_golf": "Norte",
    "alto_prado": "Norte",
    "villa_country": "Norte",
    "villa_carolina": "Norte",
    "el_limoncito": "Norte",
    "paraiso": "Norte",
    "bellavista": "Norte",
    "san_vicente": "Norte",
    "el_porvenir": "Norte",
    "betania": "Norte",
    "alameda_del_rio": "Norte",
    "la_concepcion": "Norte",
}

def determine_zone(neighborhood: str, current_zone: Optional[str] = None) -> str:
    """
    Enforces the Interface Contract invariant: zone in ('Norte', 'Noroccidente').
    1. If raw zone is already valid ('Norte' or 'Noroccidente'), preserve it.
    2. Lookup canonical normalized neighborhood in BARRIO_TO_ZONE.
    3. If unknown, scan neighborhood/address text for 'noroccidente' or 'riomar' -> 'Noroccidente'.
    4. Default fallback: 'Norte'.
    """
    clean_current = str(current_zone or "").strip()
    if clean_current in ("Norte", "Noroccidente"):
        return clean_current
    
    norm = normalize_neighborhood(neighborhood)
    if norm in BARRIO_TO_ZONE:
        return BARRIO_TO_ZONE[norm]
    
    text = f"{neighborhood} {clean_current}".lower()
    if any(k in text for k in ["noroccidente", "riomar", "mallorquin", "miramar", "santos", "campestre"]):
        return "Noroccidente"
    
    return "Norte"
```

### 3.4 Multi-Layer Defense-in-Depth Implementation Plan
1. **Layer 1 (Extractor - `data_pipeline/extractors/metrocuadrado.py`)**:
   In `normalize_listing`:
   ```python
   # Line 204: Sanitize extracted zone against allowed values
   zona_obj = itm.get("mzona") or {}
   zone_raw = zona_obj.get("nombre") if isinstance(zona_obj, dict) else None
   if zone_raw not in ("Norte", "Noroccidente"):
       zone_name = default_zone
   else:
       zone_name = zone_raw
   ```
2. **Layer 2 (Pipeline Ingestion - `data_pipeline/pipeline.py`)**:
   In `validate_listing`:
   ```python
   # Line 151: Canonical zone enforcement
   prop["zone"] = determine_zone(prop.get("neighborhood", ""), prop.get("zone", ""))
   ```
3. **Layer 3 (Deduplication Consolidation - `data_pipeline/deduplicator.py`)**:
   In `merge_cluster`:
   ```python
   # Line 334: Ensure cluster zone resolution never leaks non-standard string
   cluster_zones = [p.get("zone") for p in cluster if p.get("zone") in ("Norte", "Noroccidente")]
   if primary.get("zone") in ("Norte", "Noroccidente"):
       clean_zone = primary["zone"]
   elif cluster_zones:
       clean_zone = cluster_zones[0]
   else:
       clean_zone = determine_zone(primary.get("neighborhood", ""), primary.get("zone"))
   
   ...
   "zone": clean_zone,
   ```

*Result for Listing `MERGED-21392-M7032477-194143777`*:
- `neighborhood` = `"Ciudad Mallorquin"`.
- `determine_zone("Ciudad Mallorquin", "Otros")` returns `"Noroccidente"`.
- Constituent listing `FR-194143777` provides `"Noroccidente"`.
- `MERGED-21392-M7032477-194143777` is assigned `"Noroccidente"`, 100% satisfying `PROJECT.md § Interface Contracts`.

---

## 4. Adversarial Test Suite Inspection (`tests/test_adversarial_dedup_geo.py`)

The test suite comprises **21 unit tests** organized into **4 test classes**.

### 4.1 Suite Inventory & Verification Criteria

#### Class 1: `TestAdversarialDeduplicationSyntheticDuplicates` (3 unit tests)

1. **`test_fuzzy_price_delta_50k_and_area_delta_1m2_merged`**
   - **Target**: Fuzzy similarity scoring and attribute consolidation for duplicate pair with minor price ($50k) and area (1 m²) variances.
   - **Inputs**:
     - `prop_a`: Metrocuadrado, Miramar, total $2.150.000 COP, canon $2.000.000 COP, admin $150.000 COP, 65 m², 3 hab, 2 ban, phone `3007771690`, WhatsApp `573007771690`, image `a1.jpg`.
     - `prop_b`: Finca Raiz, Miramar, total $2.100.000 COP ($50k cheaper), canon $2.100.000 COP, admin $0, 66 m² (1 m² delta), 3 hab, 2 ban, phone `+5730` (masked), image `b1.jpg`.
   - **Current Status**: PASS.
   - **Verification Criteria**:
     1. `calculate_similarity(prop_a, prop_b) >= 0.70`.
     2. Deduplication reduces pair to exactly 1 record (`len(deduped) == 1`, `stats["merged_duplicates"] == 1`).
     3. Financial arithmetic: `total_price == 2100000` (min), `admin_fee == 150000` (max), `canon == 1950000` (`total - admin`).
     4. Contact enrichment: `phone == "3007771690"` and `whatsapp == "573007771690"`.
     5. Image gallery: `len(images) == 2` with both `a1.jpg` and `b1.jpg` included.

2. **`test_fuzzy_price_delta_100k_and_area_delta_3m2_merged`**
   - **Target**: Neighborhood synonym resolution (`Altos de Riomar` vs `Riomar`) and address matching under $100k COP price delta and 3 m² area delta.
   - **Inputs**:
     - `prop_a`: Riomar, $2.400.000 COP total, admin $0, 75 m², address `"Cra 51 # 96-30"`.
     - `prop_b`: Altos de Riomar, $2.500.000 COP total ($100k delta), admin $400.000 COP, 72 m² (3 m² delta), address `"Cra 51 # 96-30"`.
   - **Current Status**: PASS.
   - **Verification Criteria**:
     1. `calculate_similarity(prop_a, prop_b) >= 0.70`.
     2. Merged output contains 1 record with `total_price == 2400000`, `admin_fee == 400000`, `canon == 2000000`.

3. **`test_transitive_clustering_union_find`**
   - **Target**: Transitive duplicate closure via Union-Find disjoint-set data structure.
   - **Inputs**: Three listings `TRANS-A`, `TRANS-B`, `TRANS-C` on Cra 43 # 99 in Miramar (2 hab, 2 ban, areas 60, 61, 62 m², prices $2.0M, $2.05M, $2.1M). A pairs with B, B pairs with C.
   - **Current Status**: PASS.
   - **Verification Criteria**:
     1. All three records collapse into exactly 1 merged cluster (`len(deduped) == 1`).
     2. Deduplication statistics report `stats["merged_duplicates"] == 2`.
     3. Financial attributes select global optimal: `total_price == 2000000`, `admin_fee == 200000`, `canon == 1800000`.

---

#### Class 2: `TestAdversarialDeduplicationNonDuplicates` (7 unit tests)

4. **`test_different_bedrooms_in_same_building_never_merge`**
   - **Target**: Hard physical isolation gate on bedroom count mismatch.
   - **Inputs**: Same building (`"Conjunto Sorrento"`), same barrio (Miramar), same price ($2.2M), same area (60 m²), but bedrooms: 2 vs 3.
   - **Current Status**: PASS.
   - **Verification Criteria**: `calculate_similarity == 0.0`; `len(deduped) == 2`; `stats["merged_duplicates"] == 0`.

5. **`test_price_delta_exceeding_150k_never_merge`**
   - **Target**: Hard financial isolation gate when total price difference exceeds $150.000 COP.
   - **Inputs**: Same barrio, 3 hab, 2 ban, 68 m², but prices $1.800.000 vs $2.100.000 (delta = $300.000 COP).
   - **Current Status**: PASS.
   - **Verification Criteria**: `calculate_similarity == 0.0`; `len(deduped) == 2`.

6. **`test_price_delta_boundary_150001_rejected_150000_allowed`**
   - **Target**: Strict boundary condition enforcement on $150.000 COP maximum allowable price delta.
   - **Inputs**: Base listing ($2.0M) compared against listing with $2.150.000 COP (delta $150.000) and listing with $2.150.001 COP (delta $150.001).
   - **Current Status**: PASS.
   - **Verification Criteria**:
     1. Delta $150.000 COP yields `similarity >= 0.70`.
     2. Delta $150.001 COP yields `similarity == 0.0`.

7. **`test_different_bathrooms_difference_gte_2_never_merge`**
   - **Target**: Hard physical isolation gate when bathroom difference is >= 2.
   - **Inputs**: 1 bathroom vs 3 bathrooms in identical area and neighborhood.
   - **Current Status**: PASS.
   - **Verification Criteria**: `calculate_similarity == 0.0`; `len(deduped) == 2`.

8. **`test_conflicting_building_names_never_merge`**
   - **Target**: Entity conflict gate on distinct known building tokens.
   - **Inputs**: `"Edificio Sorrento"` vs `"Edificio Torino"` in Miramar, identical specs and price.
   - **Current Status**: PASS.
   - **Verification Criteria**: `calculate_similarity == 0.0`; `len(deduped) == 2`.

9. **`test_different_neighborhoods_never_merge`**
   - **Target**: Geographic isolation gate across distinct normalized neighborhoods.
   - **Inputs**: Miramar vs El Golf with identical specs and price.
   - **Current Status**: PASS.
   - **Verification Criteria**: `calculate_similarity == 0.0`; `len(deduped) == 2`.

10. **`test_large_area_difference_without_token_never_merge`**
    - **Target**: Physical area discrepancy gate (> 5 m² difference without common building token).
    - **Inputs**: 50 m² vs 65 m² in Miramar with no building token match.
    - **Current Status**: PASS.
    - **Verification Criteria**: `calculate_similarity == 0.0`; `len(deduped) == 2`.

---

#### Class 3: `TestGeographicIntegrityEmpirical` (7 unit tests)

11. **`test_exact_record_count_is_173`**
    - **Target**: Production inventory record count assertion.
    - **Current Implementation**: Asserts `len(self.listings) == 173`.
    - **Current Status**: PASS on current (dirty) database; WILL FAIL post-remediation (`172 != 173`).
    - **Verification Criteria & Critical Finding**:
      - Purging leaked external municipality listing `FR-191933365` (Puerto Colombia) reduces total verified inventory from 173 to **172**.
      - Hardcoded assertion `173` in this test directly contradicts the adversarial leakage audit.
      - **Verification Criterion**: Test assertion must be updated to expect the true clean inventory count:
        `self.assertEqual(len(self.listings), 172)` (or dynamically assert `len(self.listings) in (172, 173)`).

12. **`test_price_ceiling_and_arithmetic_all_173_records`**
    - **Target**: Strict verification of price ceiling ($2.500.000 COP) and financial arithmetic (`total_price == canon + admin_fee`).
    - **Current Status**: PASS (100% compliant across all current records).
    - **Verification Criteria**:
      1. Every listing must have `total_price <= 2500000`.
      2. Every listing must have `canon > 0` and `admin_fee >= 0`.
      3. Every listing must satisfy `total_price == canon + admin_fee`.

13. **`test_southern_barranquilla_zero_leakage`**
    - **Target**: Negative geographic filter auditing for zero occurrences of southern/southeastern Barranquilla sectors.
    - **Current Status**: PASS (0 leaks found).
    - **Verification Criteria**: No listing's `neighborhood`, `title`, `address`, or `zone` may match any of the 17 banned southern tokens (`rebolo`, `chinita`, `el bosque`, `simon bolivar`, `san roque`, `chiquinquira`, `montes`, `soledad`, `malambo`, `galapa`, `baranoa`, `sabanagrande`, `suroriente`, `suroccidente`).

14. **`test_adversarial_leakage_audit_puerto_colombia`**
    - **Target**: Auditing for external municipality leakage (specifically Puerto Colombia).
    - **Current Status**: **FAIL** (detects `FR-191933365` with `neighborhood: "Puerto colombia"`).
    - **Verification Criteria**:
      1. Count of listings where `neighborhood == "Puerto colombia"` or non-Mallorquín Puerto Colombia URL must equal `0`.
      2. `FR-191933365` must be rejected by `data_pipeline/pipeline.py`.

15. **`test_zone_interface_contract_conformance`**
    - **Target**: Schema conformity with `PROJECT.md § Interface Contracts` (`zone: string ('Norte' | 'Noroccidente')`).
    - **Current Status**: **FAIL** (detects `MERGED-21392-M7032477-194143777` with `zone: "Otros"`).
    - **Verification Criteria**:
      1. Count of listings where `zone not in ["Norte", "Noroccidente"]` must equal `0`.
      2. `MERGED-21392-M7032477-194143777` must be assigned `"Noroccidente"`.

16. **`test_bedrooms_valid_positive_count`**
    - **Target**: Physical sanity invariant that bedroom count must be a positive integer (`bedrooms >= 1`).
    - **Current Status**: **FAIL** (detects `FR-192126512` with `bedrooms == -1`).
    - **Verification Criteria**:
      1. Count of listings where `bedrooms < 1` or `bedrooms is None` must equal `0`.
      2. `FR-192126512` must have `bedrooms >= 1` (clamped or parsed as 3).

17. **`test_stratum_in_socioeconomic_range_1_to_6`**
    - **Target**: Colombian regulatory and physical invariant that socioeconomic stratum must be an integer between 1 and 6 inclusive.
    - **Current Status**: **FAIL** (detects `FR-193957120` with `stratum == 110`).
    - **Verification Criteria**:
      1. Count of listings where `stratum not in range(1, 7)` must equal `0`.
      2. `FR-193957120` must be clamped to valid stratum (`1 <= stratum <= 6`).

---

#### Class 4: `TestJsonVsCsvExactParity` (4 unit tests)

18. **`test_csv_has_utf8_bom`**
    - **Target**: Microsoft Excel Windows encoding compatibility.
    - **Current Status**: PASS.
    - **Verification Criteria**: First 3 bytes of `data/inmuebles_barranquilla.csv` must strictly match `b'\xef\xbb\xbf'`.

19. **`test_exact_row_count_match`**
    - **Target**: 1:1 row count parity between JSON and CSV, and inventory count check.
    - **Current Status**: PASS on current (dirty) database; WILL FAIL post-remediation (`172 != 173`).
    - **Verification Criteria & Critical Finding**:
      - `len(json) == len(csv)` must hold true 1:1.
      - Like test 11, line 445 (`self.assertEqual(len(self.json_data), 173)`) must be updated to expect **172** once `FR-191933365` is purged.

20. **`test_exact_id_sequence_match`**
    - **Target**: Row-by-row ID order preservation between JSON and CSV.
    - **Current Status**: PASS.
    - **Verification Criteria**: For all indices `i` from 0 to `N-1`, `json[i]["id"] == csv[i]["id"]`.

21. **`test_field_by_field_parity`**
    - **Target**: Exact field value match across all 25 CSV columns vs JSON objects.
    - **Current Status**: PASS.
    - **Verification Criteria**: 100% equality for all 25 fields across all rows, including integer types, string values, contact sub-dictionary mapping, image counts, main image, and calculated `price_per_m2` formula (`round(total_price / area_m2)`).

---

## 5. Critical Engineering Caveats Discovered

### Caveat 1: Hardcoded 173 in Tests 11 & 19 vs. Puerto Colombia Purge
- **The Conflict**: Challenger handoff requests purging `FR-191933365` to satisfy `test_adversarial_leakage_audit_puerto_colombia`. However, `FR-191933365` is an unmerged listing. Removing it decreases database row count from 173 to 172.
- **The Consequence**: If the developer purges `FR-191933365` without updating tests 11 and 19, the test run will fail with:
  `AssertionError: 172 != 173 : Database must contain exactly 173 records.`
- **Remediation**: The developer or orchestrator must align tests 11 and 19 to assert `172` (the verified post-purge inventory count).

### Caveat 2: Finca Raíz URLs for Ciudad Mallorquín Contain `puerto-colombia`
- **Observation**: Finca Raíz categorizes Ciudad Mallorquín under Puerto Colombia's municipality in its URL structure (e.g. `https://www.fincaraiz.com.co/apartamento-en-arriendo-en-ciudad-mallorquin-puerto-colombia/194143777`).
- **The Risk**: A naive filter or test searching for `"puerto-colombia" in url` would falsely reject valid `Ciudad Mallorquin` listings!
- **Protection**: `test_adversarial_dedup_geo.py` line 359 must ensure negative match for `ciudad-mallorquin`:
  ```python
  puerto_colombia_listings = [
      p for p in self.listings
      if (str(p.get("neighborhood", "")).strip().lower() == "puerto colombia"
          or ("/arriendo-en-puerto-colombia/" in str(p.get("url", "")).lower()
              and "ciudad-mallorquin" not in str(p.get("url", "")).lower()))
  ]
  ```

### Caveat 3: Whitelist Synonym Completeness to Prevent Inventory Depletion
- **Observation**: In `fallback_data.json`, 24 legitimate Northern listings are labeled with minor spelling variants: `Ciudad de Mallorquin` (7), `El Porvenir` (3), `Betania` (3), `Rio Alto` (2), `Ciudad Mallorquin Zona Urbana` (2), `Altos del Limon` (1), `Altos de San Vicente` (1), `Golf Alto Prado` (1), `El Paraiso` (1), `Villa Paraiso` (1), `Santa Monica` (1).
- **The Risk**: In `pipeline.py`, lines 156-159 allowed these to pass because `is_norte_zone` was `True`. If a developer simply replaces `is_allowed_barrio or is_norte_zone` with `norm_barrio in ALLOWED_BARRIOS` without updating `NEIGHBORHOOD_SYNONYMS`, **24 valid properties will be erroneously dropped**, reducing inventory from 173 to 149!
- **Protection**: Add these canonical synonyms to `NEIGHBORHOOD_SYNONYMS` in `data_pipeline/deduplicator.py` and `ALLOWED_BARRIOS` in `data_pipeline/pipeline.py`.

---

## 6. Synthesis & Proposed Code Modifications

### Target 1: `data_pipeline/extractors/metrocuadrado.py`
In `normalize_listing` (around line 204):
```python
<<<<
        zona_obj = itm.get("mzona") or {}
        zone_name = zona_obj.get("nombre") if isinstance(zona_obj, dict) else None
        if not zone_name:
            zone_name = default_zone
====
        zona_obj = itm.get("mzona") or {}
        raw_zone = zona_obj.get("nombre") if isinstance(zona_obj, dict) else None
        if raw_zone in ("Norte", "Noroccidente"):
            zone_name = raw_zone
        else:
            zone_name = default_zone
>>>>
```

### Target 2: `data_pipeline/pipeline.py`
In `ALLOWED_BARRIOS` and `validate_listing` (lines 24-30 and 151-192):
```python
# Add missing target synonyms and allowed neighborhoods
ALLOWED_BARRIOS = {
    "el_golf", "alto_prado", "riomar", "villa_santos", "villa_country",
    "miramar", "villa_carolina", "el_limoncito", "paraiso", "bellavista",
    "buenavista", "ciudad_mallorquin", "la_campina", "tabor", "los_alpes",
    "andalucia", "san_vicente", "la_cumbre", "ciudad_jardin", "granadillo",
    "santa_monica", "el_porvenir", "betania", "alameda_del_rio", "la_concepcion",
    "villa_campestre", "desconocido"
}

DISALLOWED_MUNICIPALITIES = {
    "puerto_colombia", "puerto colombia", "soledad", "malambo", "galapa",
    "baranoa", "sabanagrande"
}

# In validate_listing:
        barrio = prop.get("neighborhood", "")
        norm_barrio = normalize_neighborhood(barrio)
        
        # Explicit municipal leak rejection
        if norm_barrio in DISALLOWED_MUNICIPALITIES:
            return False, f"Neighborhood '{barrio}' is in an external municipality outside Barranquilla"
        if "puerto colombia" in str(prop.get("title", "")).lower() and "mallorquin" not in str(prop.get("title", "")).lower():
            return False, f"Listing title '{prop.get('title')}' is in Puerto Colombia"

        is_allowed_barrio = norm_barrio in ALLOWED_BARRIOS
        if not is_allowed_barrio:
            if norm_barrio == "desconocido" and any(z in str(prop.get("zone", "")).lower() for z in ["norte", "noroccidente", "riomar"]):
                pass
            else:
                return False, f"Neighborhood '{barrio}' not in target sector whitelist"

        # Deterministic Zone Invariant ('Norte' | 'Noroccidente')
        prop["zone"] = determine_zone(barrio, prop.get("zone"))

        # Physical clamping
        try:
            raw_beds = int(prop.get("bedrooms", 1) or 1)
            prop["bedrooms"] = max(1, raw_beds)
        except (ValueError, TypeError):
            prop["bedrooms"] = 1

        try:
            raw_stratum = int(prop.get("stratum", 4) or 4)
            prop["stratum"] = raw_stratum if 1 <= raw_stratum <= 6 else 4
        except (ValueError, TypeError):
            prop["stratum"] = 4
```

### Target 3: `data_pipeline/deduplicator.py`
In `NEIGHBORHOOD_SYNONYMS` and `merge_cluster` (line 334):
```python
# Add canonical synonyms to NEIGHBORHOOD_SYNONYMS:
    "ciudad de mallorquin": "ciudad_mallorquin",
    "ciudad mallorquin zona urbana": "ciudad_mallorquin",
    "golf alto prado": "el_golf",
    "el paraiso": "paraiso",
    "villa paraiso": "paraiso",
    "altos de san vicente": "san_vicente",
    "altos del limon": "riomar",
    "rio alto": "riomar",
    "santa monica": "santa_monica",
    "el porvenir": "el_porvenir",
    "porvenir": "el_porvenir",
    "betania": "betania",
    "conjunto residencial villa campestre": "villa_campestre",
    "villa campestre": "villa_campestre",
    "la concepcion": "la_concepcion",
    "alameda del rio": "alameda_del_rio"

# In merge_cluster:
    cluster_zones = [p.get("zone") for p in cluster if p.get("zone") in ("Norte", "Noroccidente")]
    if primary.get("zone") in ("Norte", "Noroccidente"):
        clean_zone = primary["zone"]
    elif cluster_zones:
        clean_zone = cluster_zones[0]
    else:
        clean_zone = determine_zone(primary.get("neighborhood", ""), primary.get("zone"))
    
    ...
    "zone": clean_zone,
```
