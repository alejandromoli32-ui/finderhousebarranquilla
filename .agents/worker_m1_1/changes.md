# Changes Report: Milestone 1 (M1) Implementation

**Agent**: `worker_m1_1` (Milestone 1 Worker)  
**Date**: 2026-09-13  
**Target Modules**:
1. `data_pipeline/extractors/metrocuadrado.py`
2. `data_pipeline/extractors/fincaraiz.py`
3. `data_pipeline/deduplicator.py`
4. `data_pipeline/pipeline.py`
5. `data_pipeline/fallback_data.json`
6. `tests/test_pipeline.py`
7. `data/inmuebles_barranquilla.json`
8. `data/inmuebles_barranquilla.csv`

---

## 1. Summary of Changes

Implemented a production-grade data extraction, normalization, deduplication, and export pipeline for residential rental properties in Barranquilla Norte with budget <= $2.500.000 COP monthly.

### Component Details:

### 1. `data_pipeline/extractors/metrocuadrado.py`
- Implemented `MetrocuadradoExtractor` using the Next.js RSC App Router stream (`Accept: text/x-component`, `RSC: 1`).
- Queries 20 canonical neighborhood slugs in Barranquilla Norte & Noroccidente.
- Decodes `initialResults` and `results` arrays with balanced JSON parsing.
- Maps all fields to the canonical schema specified in `PROJECT.md`.
- Normalizes unmasked phone and WhatsApp with Colombia international prefix `573...`.
- Extracts high-resolution photo URLs (converting `_p.jpg` thumbnails to `.jpg`).
- Supports offline fallback caching and atomic updates.

### 2. `data_pipeline/extractors/fincaraiz.py`
- Implemented `FincaRaizExtractor` querying SSR Next.js endpoints across 16 target sectors.
- Decodes `<script id="__NEXT_DATA__"[^>]*>` payloads.
- Extracts canon, administration fee (handling `admin_included` flags, `commonExpenses` objects, and `technicalSheet` values), ensuring `total_price == canon + admin_fee`.
- Extracts full photo galleries (CDN URLs) and detailed physical specifications.
- Supports offline fallback caching and atomic updates.

### 3. `data_pipeline/deduplicator.py`
- Implemented a Two-Tier Fuzzy Deduplication Engine:
  - **Tier 1 (Candidate Blocking)**: Blocks candidate pairs by `(norm_neighborhood, bedrooms)` where `normalize_neighborhood` strips diacritics, noise tokens, and canonicalizes synonyms.
  - **Tier 2 (Multi-Factor Scoring Matrix)**: Calculates weighted similarity $S(A, B)$ across neighborhood (0.25), bedrooms (0.25), bathrooms (0.15), area (0.15), price (0.20), and building/street token match (+0.10). Hard rejection gates on neighborhood mismatch, bedroom mismatch, price delta > $150k COP, area delta > 5m² without token match, and conflicting building names.
  - **Cluster Consolidation**: Employs Disjoint-Set Union (Union-Find) clustering for transitive linkage.
  - **Attribute Merging Matrix**: Merges duplicate records by keeping unmasked phone/WhatsApp from Metrocuadrado, high-resolution galleries from Finca Raíz, explicit administration fees, tenant-optimal minimum price, and tracks full source provenance (`source_urls` and `source_ids`).

### 4. `data_pipeline/pipeline.py`
- Implemented `PipelineController` with CLI options (`--offline`, `--max-price`, `--output-json`, `--output-csv`, `--portals`, `--verbose`).
- Enforces strict validation gates:
  - Strict price ceiling: `canon + admin_fee <= 2.500.000 COP` (exact boundary $2.500.000 allowed, $2.500.001 rejected).
  - Arithmetic integrity: `total_price == canon + admin_fee`.
  - Positive canon and non-negative admin fee.
  - Barranquilla Norte target geography.
  - URL safety (http/https).
- Atomically exports to `data/inmuebles_barranquilla.json` and `data/inmuebles_barranquilla.csv` (encoded with UTF-8 BOM `utf-8-sig` for native opening in Microsoft Excel on Windows).

### 5. `data_pipeline/fallback_data.json`
- Populated with 318 verified real rental listings in Barranquilla Norte across Metrocuadrado and Finca Raíz to ensure 100% test and pipeline reliability even during network disconnects.

### 6. `tests/test_pipeline.py`
- Implemented 21 unit tests covering:
  - Price ceiling exact boundary ($2.500.000 allowed, $2.500.001 rejected, $3.500.000 rejected)
  - Admin fee calculations ($0 admin when included or separate, negative fee rejection)
  - Cross-portal deduplication (exact duplicates, fuzzy tolerance with $80k price delta in Sorrento case, area tolerance)
  - Distinct property rejection (different rooms, different neighborhoods, different buildings)
  - Attribute merging (phone, WhatsApp, gallery combination)
  - Extractor normalization logic
  - Schema completeness for all required fields in `PROJECT.md`
  - JSON format and CSV UTF-8 BOM (`\xef\xbb\xbf`) validation.

### 7. Generated Datasets (`data/`)
- `data/inmuebles_barranquilla.json`: 173 unique, verified properties in Barranquilla Norte <= $2.500.000 COP.
- `data/inmuebles_barranquilla.csv`: 173 rows matching JSON with UTF-8 BOM.
