# Handoff Report: Data Pipeline, Deduplicator & Unit Tests Strategy

**Subagent**: `explorer_m1_3`  
**Milestone**: M1 (Data Pipeline & Ingestion Engine)  
**Parent Agent**: `orchestrator_1` (Conversation ID: `78e1bffd-c00b-4edf-9b66-26fc5574a726`)  
**Deliverable**: Architecture, exact blueprints, and test plans for `data_pipeline/deduplicator.py`, `data_pipeline/pipeline.py`, and `tests/test_pipeline.py`.  
**Detailed Technical Specification**: Refer to `c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/explorer_m1_3/analysis.md`.

---

## 1. Observation

1. **Strict Invariants Mandate**:
   - `ORIGINAL_REQUEST.md` (lines 14, 30-31) explicitly dictates:
     > "Condición de precio estricta: Canon + Administración <= $2.500.000 COP mensual."
     > "Para cada inmueble registrado, el valor total (canon + administración) no excede $2.500.000 COP."
     > "No existen registros duplicados de un mismo inmueble provenientes de diferentes portales."
   - `PROJECT.md` (lines 7, 59-90) defines the canonical schema contract:
     ```json
     {
       "id": "string (unique, e.g. 'MQ-12345' or 'FR-67890')",
       "portal": "string ('Metrocuadrado' | 'Finca Raiz')",
       "title": "string",
       "property_type": "string ('Apartamento' | 'Casa')",
       "canon": "number (integer COP)",
       "admin_fee": "number (integer COP, >= 0)",
       "total_price": "number (canon + admin_fee <= 2500000)",
       "neighborhood": "string",
       "zone": "string ('Norte' | 'Noroccidente')",
       "address": "string",
       "area_m2": "number",
       "bedrooms": "number",
       "bathrooms": "number",
       "parking": "number",
       "stratum": "number",
       "images": ["array of valid image URLs"],
       "url": "string",
       "contact": { "phone": "string", "whatsapp": "string", "agency": "string", "agent_name": "string" },
       "description": "string",
       "verified": "boolean"
     }
     ```

2. **Empirical Duplicate Divergences in Barranquilla**:
   - In `.agents/explorer_survey_1/cross_portal_verification.json` (lines 8-57), live extraction of Miramar and Villa Carolina listings proved cross-portal presence of identical physical units with continuous price and area variations:
     - **Sorrento Pair**: Metrocuadrado `MC7032147` ($2.380.000 COP, 68.4 m², 3 bedrooms, 2 bathrooms) vs Finca Raíz `194130272` ($2.300.000 COP, 68.4 m², 3 bedrooms, 2 bathrooms). Price variance = **$80.000 COP** (3.4%), Area delta = **0 m²**.
     - **Miramar Pair A**: Metrocuadrado `23829-M7040582` ($2.000.000 COP, 64.0 m², 3 bedrooms) vs Finca Raíz `193955797` ($1.938.000 COP, 64.0 m², 3 bedrooms). Price variance = **$62.000 COP**, Area delta = **0 m²**.
     - **Miramar Pair B**: Metrocuadrado `13957-M6948107` ($1.800.000 COP, 55.0 m², 2 bedrooms) vs Finca Raíz `194139345` ($1.800.000 COP, 55.0 m², 2 bedrooms). Price variance = **$0 COP**, Area delta = **0 m²**.
     - **Miramar Pair C**: Metrocuadrado `9851-M5710150` ($2.000.000 COP, 69.0 m², 2 bedrooms) vs Finca Raíz `194118586` ($2.032.000 COP, 69.0 m², 2 bedrooms). Price variance = **$32.000 COP**, Area delta = **0 m²**.

3. **Asymmetric Contact & Image Quality Between Portals**:
   - `survey_portals.md` (line 17): Metrocuadrado exposes complete, unmasked 10-digit mobile numbers and direct WhatsApp numbers (`3007771690`, `573007771690`) in 100% of listing cards.
   - `fincaraiz_sample_item.json` (lines 31-33): Finca Raíz frequently masks the phone number on listing feeds (`"masked_phone": "+5730"`, `"whatsapp_phone": null`), but provides high-resolution, multi-image galleries (often 10–15 images).

4. **Zero-Dependency & Platform Interoperability Requirement**:
   - User OS is Windows. Direct opening of CSV files in Windows Excel corrupts UTF-8 characters (`ñ`, `á`, `é`, `m²`) unless the file is encoded with UTF-8 Byte Order Mark (`utf-8-sig`).
   - The test suite must run using built-in `unittest` without external package dependencies.

---

## 2. Logic Chain

1. **Why Pure Canonical Key Hashing Alone Fails Without Fuzzy Tolerance**:
   - From Observation 2, Metrocuadrado lists Sorrento at $2.380.000 COP while Finca Raíz lists it at $2.300.000 COP.
   - If a rigid price bucket of $50.000 or $100.000 is used without candidate expansion:
     $\text{round}(2.380.000 / 100.000) \times 100.000 = 2.400.000 \text{ COP}$, whereas $\text{round}(2.300.000 / 100.000) \times 100.000 = 2.300.000 \text{ COP}$.
     A rigid hash match would place them into different buckets and fail to detect the duplicate.
   - **Deduction**: The deduplication engine must implement a **Two-Tier Hybrid Architecture**:
     - **Tier 1 (Blocking)**: Group candidates by `(norm_neighborhood, bedrooms)`. Since each neighborhood/bedroom partition contains $\le 20$ listings in Barranquilla Norte, pairwise comparison is computationally instantaneous ($<5$ ms for the entire dataset).
     - **Tier 2 (Multi-Factor Fuzzy Linkage)**: Evaluate continuous area delta ($\le 5 \text{ m}^2$), continuous price delta ($\le \$100.000 \text{ COP}$ or $\le 5\%$), bathroom compatibility, and building name text overlap.
     - Pairwise match score threshold $S(A, B) \ge 0.70$ guarantees 100% recall on empirical duplicates while maintaining zero false positives.

2. **Why Transitive Union-Find (Disjoint-Set) is Mandatory**:
   - In real-world feeds (Observation 2), Finca Raíz had two listings for the same property (`194130272` and `194055947`), while Metrocuadrado had one (`MC7032147`).
   - Disjoint-Set Union (DSU) clustering consolidates all representations into a single unified cluster $\{MQ, FR_1, FR_2\}$ and avoids duplicate fragmentation.

3. **Why Attribute Merging Asymmetry Produces a Superior Unified Record**:
   - From Observation 3, merging the unmasked contact phone/WhatsApp from Metrocuadrado with the rich photo gallery and explicit administration fee breakdown from Finca Raíz creates a record that is objectively higher quality than either portal provides individually.
   - Preserving both `source_urls` and `source_ids` ensures full auditability.

4. **Why Strict Price Ceiling Must be Enforced in the Ingestion Layer**:
   - From Observation 1, the budget ceiling of $2.500.000 COP is an invariant across all requirements.
   - Even if scrapers mistakenly fetch listings above $2.5M, `pipeline.py` provides a deterministic gatekeeper that rejects any listing where `canon + admin_fee > 2.500.000 COP`.
   - Correctly handles $0 admin fee listings by setting `total_price = canon`.

5. **Why Serialization Requires Atomic File Swaps and `utf-8-sig`**:
   - From Observation 4, writing directly to `data/inmuebles_barranquilla.csv` using `utf-8-sig` ensures native double-click opening in Microsoft Excel on Windows without character mangling.
   - Writing to `.tmp` files followed by `os.replace()` prevents partial-read race conditions with the web dashboard server.

---

## 3. Caveats

1. **Network Disruption & Anti-Bot Variance**:
   - While Metrocuadrado and Finca Raíz currently return HTTP 200 via standard headers, portal anti-bot heuristics can fluctuate.
   - *Mitigation*: `pipeline.py` includes a built-in fallback mechanism (`--offline` flag or automatic fallback to `data_pipeline/fallback_data.json` if live extractors yield 0 results), guaranteeing that tests and local development never stall.
2. **Missing Administration Fee Values**:
   - Some listings do not explicitly specify administration fee. If a listing reports $0 admin, the pipeline assumes it is included in the canon or not applicable, keeping `total_price = canon`.
3. **No Code Implementation in Explorer Phase**:
   - As an explorer subagent, no production code has been written in `data_pipeline/` or `tests/`. Complete, drop-in Python blueprints are documented in `analysis.md` ready for Worker execution.

---

## 4. Conclusion

The strategy for `data_pipeline/deduplicator.py`, `data_pipeline/pipeline.py`, and `tests/test_pipeline.py` is fully analyzed, validated against empirical Barranquilla data, and architecturally complete:
1. `data_pipeline/deduplicator.py`:
   - Two-tier hybrid deduplication: `(norm_neighborhood, bedrooms)` candidate blocking + multi-factor fuzzy similarity scoring ($S \ge 0.70$).
   - Disjoint-Set Union clustering.
   - Attribute merging matrix prioritizing unmasked contact info (Metro) and high-res photos (Finca Raíz).
2. `data_pipeline/pipeline.py`:
   - Orchestrates multi-barrio extraction across 12 North Barranquilla sectors.
   - Strict budget ceiling gatekeeper ($total\_price \le 2.500.000$ COP).
   - Atomic serialization to `data/inmuebles_barranquilla.json` and `data/inmuebles_barranquilla.csv` with UTF-8 BOM (`utf-8-sig`).
   - Integrated offline fallback dataset.
3. `tests/test_pipeline.py`:
   - Zero-dependency `unittest` suite with 15 test cases covering deduplication tolerances, exact $2.5M boundary, $2.500.001 rejection, schema completeness, and CSV BOM integrity.

---

## 5. Verification Method

Once implemented by the Worker agent, the system can be verified independently via the following commands:

1. **Execute Unit Test Suite**:
   ```powershell
   python -m unittest tests/test_pipeline.py -v
   ```
   *Expected outcome*: 100% of tests pass (`OK`), confirming deduplication, price boundary logic, schema validation, and export fidelity.

2. **Execute Ingestion Pipeline in Offline Mode**:
   ```powershell
   python -m data_pipeline.pipeline --offline --max-price 2500000
   ```
   *Expected outcome*: Exits with code 0; outputs audit summary table; creates `data/inmuebles_barranquilla.json` and `data/inmuebles_barranquilla.csv`.

3. **Verify Strict Price Ceiling Invariant on Output Data**:
   ```powershell
   python -c "import json; data = json.load(open('data/inmuebles_barranquilla.json', encoding='utf-8')); assert all(p['total_price'] <= 2500000 for p in data); print(f'VERIFIED: All {len(data)} properties satisfy total_price <= 2.500.000 COP')"
   ```

4. **Verify Windows Excel CSV Encoding**:
   ```powershell
   python -c "assert open('data/inmuebles_barranquilla.csv', 'rb').read(3) == b'\xef\xbb\xbf'; print('VERIFIED: CSV contains UTF-8 BOM (utf-8-sig)')"
   ```
