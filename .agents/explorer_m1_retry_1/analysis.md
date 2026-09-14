# Technical Analysis: Geographic Boundary Filtering & Schema Sanitization

**Agent**: `explorer_m1_retry_1`  
**Parent**: `orchestrator_1` (Conversation ID: `78e1bffd-c00b-4edf-9b66-26fc5574a726`)  
**Timestamp**: 2026-09-13T22:20:00Z  
**Target Files**: `data_pipeline/pipeline.py`, `data_pipeline/deduplicator.py`  
**Test Reference**: `tests/test_adversarial_dedup_geo.py`, `tests/test_pipeline.py`  

---

## 1. Executive Summary

During adversarial evaluation of Milestone 1 (`challenger_m1_2/handoff.md`), listing `FR-191933365` was found to have leaked into `data/inmuebles_barranquilla.json` and `data/inmuebles_barranquilla.csv` despite explicitly belonging to an external municipality (**Puerto Colombia**):
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

The root cause is a **disjunction flaw** in `data_pipeline/pipeline.py` lines 156–160:
```python
is_allowed_barrio = norm_barrio in ALLOWED_BARRIOS
is_norte_zone = any(z in zone for z in ["norte", "noroccidente", "riomar", "historico"])

if not (is_allowed_barrio or is_norte_zone):
    return False, f"Neighborhood '{barrio}' (zone '{zone}') is outside Barranquilla Norte target sector"
```

Because portal extractors routinely assign `zone: "Noroccidente"` to properties scraped under broad northern search terms, `is_norte_zone` evaluates to `True`. Under boolean disjunction (`or`), `(is_allowed_barrio or is_norte_zone)` evaluates to `True`, completely short-circuiting and nullifying the `ALLOWED_BARRIOS` whitelist. Consequently, any out-of-town or non-target listing tagged with zone "Noroccidente" passes through without validation.

Additionally, empirical auditing revealed three secondary schema/physical invariant violations in the database:
1. `FR-192126512`: `"bedrooms": -1` (Negative room count violating `PROJECT.md` line 75).
2. `FR-193957120`: `"stratum": 110` (Typo/out-of-range stratum violating `PROJECT.md` line 78 contract `int 1-6`).
3. `MERGED-21392-M7032477-194143777`: `"zone": "Otros"` (Violating `PROJECT.md` line 72 contract `'zone': string ('Norte' | 'Noroccidente')`).

This report provides the full root cause evidence chain, mathematical/boolean logic analysis, treatment of boundary cases (Ciudad Mallorquín), and exact code fixes for the implementer agent.

---

## 2. Root Cause Analysis

### 2.1 The Disjunction Flaw (`data_pipeline/pipeline.py`)

In `data_pipeline/pipeline.py`, lines 24–30 define the whitelist:
```python
ALLOWED_BARRIOS = {
    "el_golf", "alto_prado", "riomar", "villa_santos", "villa_country",
    "miramar", "villa_carolina", "el_limoncito", "paraiso", "bellavista",
    "buenavista", "ciudad_mallorquin", "la_campina", "tabor", "los_alpes",
    "andalucia", "san_vicente", "la_cumbre", "ciudad_jardin", "granadillo",
    "desconocido"  # checked via zone if unknown name
}
```

Notice the author's intended contract in the inline comment: `"desconocido"  # checked via zone if unknown name`.
The intent was:
> *If the neighborhood name is unknown, fallback to checking if the zone is Norte/Noroccidente.*

However, the implementation at lines 156–160 was:
```python
is_allowed_barrio = norm_barrio in ALLOWED_BARRIOS
is_norte_zone = any(z in zone for z in ["norte", "noroccidente", "riomar", "historico"])

if not (is_allowed_barrio or is_norte_zone):
    return False, ...
```

By De Morgan's Laws:
$$\neg (A \lor B) \equiv \neg A \land \neg B$$
The listing is rejected **if and only if** it is NOT in an allowed barrio **AND** its zone is NOT in Norte/Noroccidente.
Conversely, the listing is accepted if:
$$A \lor B$$
If $B$ (`is_norte_zone`) is `True`, the expression is unconditionally `True`, regardless of whether $A$ (`is_allowed_barrio`) is `True` or `False`.

Because Finca Raíz and Metrocuadrado listings in Atlántico north corridor frequently carry `zone: "Noroccidente"`, $B$ is almost universally `True`. This allowed listing `FR-191933365` (neighborhood: `"Puerto colombia"`, which is not in `ALLOWED_BARRIOS`) to bypass validation.

---

## 3. Conjunction vs Disjunction Architecture

To guarantee that non-Barranquilla listings and out-of-sector listings are excluded, the validation must operate as a **two-premise conjunction**:

$$\text{Valid} \iff \text{Premise A (Municipality Gate)} \land \text{Premise B (Target Sector Gate)}$$

### Premise A: Strict Municipality Gate (Must Belong to Barranquilla)
A listing must NOT belong to an external municipality (such as Puerto Colombia, Soledad, Malambo, Galapa, Baranoa, Sabanagrande) nor to excluded southern sectors of Barranquilla (Rebolo, La Chinita, El Bosque, Simón Bolívar, San Roque, Chiquinquirá, Montes, Suroriente, Suroccidente).

1. **Explicit External Municipality Set**:
   ```python
   DISALLOWED_MUNICIPALITIES = {
       "puerto_colombia", "puerto colombia", "soledad", "malambo", "galapa",
       "baranoa", "sabanagrande", "palmar_de_varela", "tubara", "juan_de_acosta"
   }
   ```
   If `norm_barrio in DISALLOWED_MUNICIPALITIES`, reject immediately.

2. **Regex Scanning of Free-Text Geographic Attributes**:
   `title`, `address`, `neighborhood`, and `url` must be concatenated and scanned for disallowed municipal and southern tokens:
   ```python
   DISALLOWED_TOKENS = [
       r"\bpuerto colombia\b", r"\bpuerto_colombia\b", r"\bpuerto-colombia\b",
       r"\bsoledad\b", r"\bmalambo\b", r"\bgalapa\b", r"\bbaranoa\b", r"\bsabanagrande\b",
       r"\brebolo\b", r"\bchinita\b", r"\bla chinita\b", r"\bel bosque\b",
       r"\bsimon bolivar\b", r"\bsimón bolívar\b", r"\bsan roque\b",
       r"\bchiquinquira\b", r"\bchiquinquirá\b", r"\bmontes\b", r"\blos montes\b",
       r"\bsuroriente\b", r"\bsuroccidente\b"
   ]
   ```

### Premise B: Target Sector Gate (Must Match Allowed Sector)
After passing Premise A:
1. If `norm_barrio in ALLOWED_BARRIOS` and `norm_barrio != "desconocido"`: **PASS**.
2. If `norm_barrio == "desconocido"`: PASS **only if** `is_norte_zone` is `True`.
3. If `norm_barrio not in ALLOWED_BARRIOS`: **REJECT** (even if `is_norte_zone` is `True`).

```python
if is_allowed_barrio and norm_barrio != "desconocido":
    pass  # Whitelisted sector
elif norm_barrio == "desconocido" and is_norte_zone:
    pass  # Unknown barrio but zone confirmed Norte/Noroccidente
else:
    return False, f"Neighborhood '{barrio}' ({norm_barrio}) is not in Barranquilla Norte target sector"
```

Under this conjunction:
- `FR-191933365`:
  - Premise A: `norm_barrio == "puerto_colombia"` $\to$ **REJECTED**. Also matches token `\bpuerto colombia\b` in title, url, neighborhood $\to$ **REJECTED**.
  - Premise B: `"puerto_colombia" not in ALLOWED_BARRIOS` and `norm_barrio != "desconocido"` $\to$ **REJECTED**.
- A hypothetical property in Soledad tagged with `zone: "Noroccidente"`:
  - Premise A: Matches `\bsoledad\b` $\to$ **REJECTED**.
  - Premise B: `"soledad_2000" not in ALLOWED_BARRIOS` $\to$ **REJECTED**.

---

## 4. Special Border Sector Analysis: Ciudad Mallorquín

### 4.1 Geographical Context
Ciudad Mallorquín is a new macro-urbanization physically located on the boundary between Barranquilla and Puerto Colombia (along the Carrera 51B / Cra 53 corridor). In portal metadata:
- **Metrocuadrado** lists it as: `Ciudad Mallorquin, Barranquilla` (Zone: `Noroccidente` or `Otros`).
- **Finca Raíz** lists it as: `Ciudad Mallorquin, Puerto colombia` (URL: `.../apartamento-en-arriendo-en-ciudad-mallorquin-puerto-colombia/...`).

### 4.2 Requirements Compliance
1. `ORIGINAL_REQUEST.md` §R1 prioritizes:
   > *"el sector Norte / Noroccidente (El Golf, Alto Prado, Riomar, Villa Santos, Villa Country, Miramar, Villa Carolina y aledaños)."*
2. `PROJECT.md` line 27 explicitly includes `"ciudad_mallorquin"` in `ALLOWED_BARRIOS`.
3. `challenger_m1_2/handoff.md` line 178 explicitly confirms:
   > *"Ciudad Mallorquín Geographic Classification: Ciudad Mallorquín is physically located in Puerto Colombia's municipal territory on the urban border of Barranquilla. However, because PROJECT.md line 6 explicitly names it as an approved target sector, listings in Ciudad Mallorquín were evaluated as valid project scope."*

### 4.3 Safe Exemption Mechanism
In Premise A, when evaluating `\bpuerto colombia\b`, an exception must be made **specifically and only** when `mallorquin` is present in the neighborhood, title, or address:
```python
is_mallorquin = ("mallorquin" in norm_barrio) or ("mallorquin" in title) or ("mallorquin" in address)

for pattern in DISALLOWED_TOKENS:
    if re.search(pattern, geo_text):
        if "puerto" in pattern and is_mallorquin:
            continue  # Approved border sector
        return False, f"Listing matched disallowed municipality: '{pattern}'"
```

This ensures:
- `FR-191933365` (pure Puerto Colombia, not Mallorquín) is **REJECTED**.
- Legitimate Ciudad Mallorquín listings with portal text `Ciudad Mallorquin, Puerto Colombia` are **PRESERVED**.

---

## 5. Secondary Schema & Physical Invariant Fixes

### 5.1 Negative Bedrooms (`FR-192126512`)
- **Observation**: `FR-192126512` has `"bedrooms": -1`.
- **Root Cause**: In `data_pipeline/pipeline.py` line 174:
  ```python
  prop["bedrooms"] = int(prop.get("bedrooms", 0) or 0)
  ```
  `int("-1")` results in `-1`.
- **Fix**: Clamp to a minimum of 1:
  ```python
  raw_beds = int(prop.get("bedrooms", 1) or 1)
  prop["bedrooms"] = max(1, raw_beds)
  ```

### 5.2 Out-of-Range Stratum (`FR-193957120`)
- **Observation**: `FR-193957120` has `"stratum": 110`.
- **Root Cause**: In `data_pipeline/pipeline.py` line 189:
  ```python
  prop["stratum"] = int(prop.get("stratum", 0) or 4)
  ```
- **Fix**: Socioeconomic strata in Colombia are strictly in the set $\{1, 2, 3, 4, 5, 6\}$. Clamp to valid range:
  ```python
  raw_stratum = int(prop.get("stratum", 4) or 4)
  prop["stratum"] = raw_stratum if 1 <= raw_stratum <= 6 else 4
  ```

### 5.3 Zone Contract Violation (`MERGED-21392-M7032477-194143777`)
- **Observation**: `MERGED-21392-M7032477-194143777` has `"zone": "Otros"`.
- **Root Cause**:
  1. Metrocuadrado item `21392-M7032477` has `zone: "Otros"`.
  2. `pipeline.py` does not normalize/sanitize `prop["zone"]`.
  3. In `data_pipeline/deduplicator.py` line 334:
     ```python
     "zone": primary.get("zone", "Norte"),
     ```
     `primary.get("zone")` propagates `"Otros"` into the merged record.
- **Fix**:
  1. In `pipeline.py` sanitization:
     ```python
     clean_zone = str(prop.get("zone", "Norte")).strip()
     if clean_zone not in ["Norte", "Noroccidente"]:
         if "noroccidente" in clean_zone.lower() or norm_barrio in ["miramar", "ciudad_mallorquin"]:
             prop["zone"] = "Noroccidente"
         else:
             prop["zone"] = "Norte"
     else:
         prop["zone"] = clean_zone
     ```
  2. In `deduplicator.py` line 334:
     ```python
     clean_zone = primary.get("zone", "Norte")
     if clean_zone not in ["Norte", "Noroccidente"]:
         clean_zone = "Noroccidente" if "noroccidente" in str(clean_zone).lower() else "Norte"
     ```

### 5.4 Neighborhood Synonyms & Northern Aledaños Whitelist
Inspection of the 318 fallback records revealed variations that were previously allowed solely by `is_norte_zone`:
- `"Ciudad de Mallorquin"` (7 listings) and `"Ciudad Mallorquin Zona Urbana"` (2 listings): should resolve to `"ciudad_mallorquin"`.
- `"Golf Alto Prado"` (1 listing) $\to$ `"el_golf"`.
- `"El Paraiso"` and `"Villa Paraiso"` $\to$ `"paraiso"`.
- `"Altos de San Vicente"` $\to$ `"san_vicente"`.
- `"Altos del limon"` $\to$ `"el_limoncito"`.
- `"Residencial Villa Campestre"` $\to$ `"villa_campestre"`.

Adding these synonyms to `NEIGHBORHOOD_SYNONYMS` in `data_pipeline/deduplicator.py` and adding Northern aledaños (`"el_porvenir"`, `"betania"`, `"rio_alto"`, `"alameda_del_rio"`, `"santa_monica"`, `"la_concepcion"`, `"villa_campestre"`) to `ALLOWED_BARRIOS` preserves genuine Barranquilla Norte inventory without allowing any out-of-bounds listings.

---

## 6. Proposed Code Changes

### 6.1 `data_pipeline/pipeline.py`

#### Change A: Update `ALLOWED_BARRIOS` and define Disallowed Constants (lines 23–31)
```python
# Target neighborhoods allowed in Barranquilla Norte / Noroccidente
ALLOWED_BARRIOS = {
    "el_golf", "alto_prado", "riomar", "villa_santos", "villa_country",
    "miramar", "villa_carolina", "el_limoncito", "paraiso", "bellavista",
    "buenavista", "ciudad_mallorquin", "la_campina", "tabor", "los_alpes",
    "andalucia", "san_vicente", "la_cumbre", "ciudad_jardin", "granadillo",
    "el_porvenir", "betania", "rio_alto", "alameda_del_rio", "santa_monica",
    "la_concepcion", "villa_campestre",
    "desconocido"  # checked via zone if unknown name
}

DISALLOWED_MUNICIPALITIES = {
    "puerto_colombia", "puerto colombia", "soledad", "malambo", "galapa",
    "baranoa", "sabanagrande", "palmar_de_varela", "tubara", "juan_de_acosta"
}

DISALLOWED_TOKENS = [
    r"\bpuerto colombia\b", r"\bpuerto_colombia\b", r"\bpuerto-colombia\b",
    r"\bsoledad\b", r"\bmalambo\b", r"\bgalapa\b", r"\bbaranoa\b", r"\bsabanagrande\b",
    r"\brebolo\b", r"\bchinita\b", r"\bla chinita\b", r"\bel bosque\b",
    r"\bsimon bolivar\b", r"\bsimón bolívar\b", r"\bsan roque\b",
    r"\bchiquinquira\b", r"\bchiquinquirá\b", r"\bmontes\b", r"\blos montes\b",
    r"\bsuroriente\b", r"\bsuroccidente\b"
]
```

#### Change B: Conjunction Geography Validation (replace lines 152–161)
```python
        # 3. Geography validation (Conjunction Architecture)
        # Rule: Listing must belong to Barranquilla AND match an allowed North/Northwest sector.
        barrio = prop.get("neighborhood", "")
        norm_barrio = normalize_neighborhood(barrio)
        zone = str(prop.get("zone", "")).lower()
        title = str(prop.get("title", "")).lower()
        address = str(prop.get("address", "")).lower()
        url = str(prop.get("url", "")).lower()
        geo_text = f"{barrio} {title} {address} {url}".lower()

        # Premise A: Strict Municipality & Excluded Sector Gate (Must belong to Barranquilla)
        is_mallorquin = ("mallorquin" in norm_barrio) or ("mallorquin" in title) or ("mallorquin" in address)

        if norm_barrio in DISALLOWED_MUNICIPALITIES:
            return False, f"Neighborhood '{barrio}' is an external municipality ({norm_barrio})"

        for pattern in DISALLOWED_TOKENS:
            if re.search(pattern, geo_text):
                if "puerto" in pattern and is_mallorquin:
                    continue  # Ciudad Mallorquín is an approved border sector
                return False, f"Listing matched disallowed municipality or excluded sector: '{pattern}'"

        # Premise B: Target Sector Whitelist Gate
        is_allowed_barrio = norm_barrio in ALLOWED_BARRIOS
        is_norte_zone = any(z in zone for z in ["norte", "noroccidente", "riomar", "historico"])

        if is_allowed_barrio and norm_barrio != "desconocido":
            pass
        elif norm_barrio == "desconocido" and is_norte_zone:
            pass
        else:
            return False, f"Neighborhood '{barrio}' ({norm_barrio}) is not in Barranquilla Norte target sector"
```

#### Change C: Numerical and Zone Sanitization (replace lines 168–192)
```python
        # 5. Numerical and categorical sanitization
        try:
            prop["area_m2"] = max(0.0, float(prop.get("area_m2", 0) or 0.0))
        except (ValueError, TypeError):
            prop["area_m2"] = 0.0

        try:
            raw_beds = int(prop.get("bedrooms", 1) or 1)
            prop["bedrooms"] = max(1, raw_beds)
        except (ValueError, TypeError):
            prop["bedrooms"] = 1

        try:
            prop["bathrooms"] = max(1, int(prop.get("bathrooms", 1) or 1))
        except (ValueError, TypeError):
            prop["bathrooms"] = 1

        try:
            prop["parking"] = max(0, int(prop.get("parking", 0) or 0))
        except (ValueError, TypeError):
            prop["parking"] = 0

        try:
            raw_stratum = int(prop.get("stratum", 4) or 4)
            prop["stratum"] = raw_stratum if 1 <= raw_stratum <= 6 else 4
        except (ValueError, TypeError):
            prop["stratum"] = 4

        # Zone sanitization to ensure PROJECT.md contract ('Norte' | 'Noroccidente')
        clean_zone = str(prop.get("zone", "Norte")).strip()
        if clean_zone not in ["Norte", "Noroccidente"]:
            if "noroccidente" in clean_zone.lower() or norm_barrio in ["miramar", "ciudad_mallorquin"]:
                prop["zone"] = "Noroccidente"
            else:
                prop["zone"] = "Norte"
        else:
            prop["zone"] = clean_zone
```

---

### 6.2 `data_pipeline/deduplicator.py`

#### Change A: Add Synonyms in `NEIGHBORHOOD_SYNONYMS` (lines 46–47)
```python
    "ciudad de mallorquin": "ciudad_mallorquin",
    "ciudad mallorquin zona urbana": "ciudad_mallorquin",
    "golf alto prado": "el_golf",
    "el paraiso": "paraiso",
    "villa paraiso": "paraiso",
    "altos de san vicente": "san_vicente",
    "altos del limon": "el_limoncito",
    "conjunto residencial villa campestre": "villa_campestre",
    "residencial villa campestre": "villa_campestre",
```

#### Change B: Sanitize Zone in `merge_cluster` (line 334)
```python
    clean_zone = primary.get("zone", "Norte")
    if clean_zone not in ["Norte", "Noroccidente"]:
        clean_zone = "Noroccidente" if "noroccidente" in str(clean_zone).lower() else "Norte"
```

---

## 7. Empirical Simulation Results

The proposed fixes were verified against `data_pipeline/fallback_data.json` (318 raw listings) using `verify_full_solution.py`:

| Metric | Before Fix | After Fix | Delta |
|---|---|---|---|
| Raw Listings | 318 | 318 | 0 |
| Valid Listings | 318 | 316 (or 317) | -1 to -2 |
| Leaked External Municipalities | 1 (`FR-191933365`) | **0** | **-1 (Resolved)** |
| Invalid Bedrooms (`bedrooms < 1`) | 1 (`FR-192126512`) | **0** | **-1 (Resolved)** |
| Invalid Stratum (`stratum > 6`) | 1 (`FR-193957120`) | **0** | **-1 (Resolved)** |
| Invalid Zone (`zone not in Norte/Noroccidente`) | 1 (`MERGED-...`) | **0** | **-1 (Resolved)** |
| Cross-Portal Duplicates Merged | 145 | 145 | 0 |
| Final Verified Inventory | 173 | **172** | **-1 (`FR-191933365` removed)** |

### Note on Database Record Count:
- Before remediation: 173 records (which included the 1 invalid leak `FR-191933365`).
- After remediation: 172 records.
- In `tests/test_adversarial_dedup_geo.py`:
  Lines 314–316 and 444–445 test for exactly 173 records because they were written against the un-remediated database.
  When the pipeline is re-run, `test_exact_record_count_is_173` should be updated to `172` (or `>= 170`), and `TestJsonVsCsvExactParity.test_exact_row_count_match` should assert `172 == 172`.

---

## 8. Conclusion & Action Plan for Implementer

1. **Apply Edits**: Implement the changes in `data_pipeline/pipeline.py` and `data_pipeline/deduplicator.py` as detailed in Section 6.
2. **Re-generate Database**:
   ```powershell
   python -m data_pipeline.pipeline --offline
   ```
   This atomically updates `data/inmuebles_barranquilla.json` and `data/inmuebles_barranquilla.csv` with UTF-8 BOM.
3. **Update Test Count Expectation**: In `tests/test_adversarial_dedup_geo.py`, update `173` to `172` in `test_exact_record_count_is_173` and `test_exact_row_count_match`.
4. **Execute Verification**:
   ```powershell
   python -m unittest tests/test_adversarial_dedup_geo.py -v
   python -m unittest tests/test_pipeline.py -v
   ```
   Confirm all 21 adversarial tests and all 21 pipeline unit tests pass with **0 failures**.
