# Opaque-Box E2E Testing Infrastructure Specification
## Tracker de Apartamentos y Casas en Arriendo — Barranquilla Norte (≤ $2.500.000 COP)

**Document Version**: 1.0.0  
**Milestone**: M-E2E — Opaque-Box End-to-End Testing Suite  
**Target Environment**: Windows (PowerShell / cmd) · Python 3.12 Standard Library (Zero External Dependencies)  
**Status**: ACTIVE & RATIFIED  

---

## 1. Testing Philosophy & Opaque-Box Principles

### 1.1 The Opaque-Box Paradigm
Opaque-box (black-box) testing validates a software system solely through its public observable contracts, interfaces, and artifacts, without coupling tests to internal implementation details, private functions, or internal monkey-patching.

In this project, opaque-box boundaries comprise:
1. **The Data Boundary**: Physical persistence files (`data/inmuebles_barranquilla.json`, `data/inmuebles_barranquilla.csv`, `data/dossier_curado.json`, `data/user_tracking.json`).
2. **The HTTP Network Boundary**: Standard HTTP/1.1 requests and responses served by `run_dashboard.py` (MIME types, HTTP status codes, CORS headers, REST payloads).
3. **The User Experience & Filtering Boundary**: Public state contracts defined by client-side queries, multi-criteria filters, and localStorage synchronization.
4. **The Curated Intelligence Boundary**: Formatted markdown deliverables (`DOSSIER_VISITAS.md`), MFVI scoring rules, and WhatsApp click-to-chat deep links (`https://wa.me/57...`).

### 1.2 Zero-Internal Mocking Policy
- Tests do not mock internal private methods or replace application classes with trivial stubs.
- Every HTTP assertion executes against a live, multi-threaded HTTP server bound to loopback `127.0.0.1`.
- Every data assertion reads from disk and parses genuine serialized datasets.
- Every state transition exercises genuine atomic filesystem writes and JSON deserialization.
- **Integrity Guarantee**: All test verifications represent real runtime operations. No test hardcodes dummy results or bypasses core domain logic.

### 1.3 Zero-Dependency Host Architecture
To prevent execution failures on Windows hosts caused by PowerShell script execution policies (e.g. Restricted `.ps1` execution affecting `pytest.ps1` or `npx.ps1`), the E2E testing framework is built entirely on **Python 3.12's native `unittest`** framework. It requires zero third-party packages (`pip install` free) and executes out-of-the-box on standard Python installations.

---

## 2. Four-Tier Testing Methodology

The testing infrastructure is structured into four distinct, progressive tiers designed to validate every layer from basic feature conformance to complex real-world user journeys.

```
┌────────────────────────────────────────────────────────────────────────┐
│               TIER 4: REAL-WORLD APPLICATION SCENARIOS                 │
│    (4 End-to-End User Journeys: Professional, Executive, Family, Fast) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│              TIER 3: CROSS-FEATURE INTERACTION SUITE                   │
│   (Faceted Filters + Search + Local Persistence + Dossier Sync)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│              TIER 2: BOUNDARY & CORNER CASE HARDENING                  │
│   (Exact $2.5M Ceiling, >$2.5M Dropping, $0 Admin, Degenerate Payloads)│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│                 TIER 1: FEATURE CONTRACT COVERAGE                      │
│    (Requirement R1: Data, Requirement R2: Dashboard, R3: Dossier)      │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Tier 1: Feature Contract Coverage (Category-Partition Testing)
Decomposes requirements R1, R2, and R3 into functional partitions and ensures that every contract invariant is met with at least 5 discrete automated test cases per requirement:
- **Requirement R1 (Multi-Portal Database & Pipeline)**:
  - Database accessibility and record existence.
  - Strict price ceiling: $\forall p \in \text{DB}: \text{total\_price} \le 2.500.000\text{ COP}$ and $\text{total\_price} = \text{canon} + \text{admin\_fee}$.
  - Schema integrity: 100% presence of required fields (`id`, `title`, `property_type`, `canon`, `admin_fee`, `total_price`, `neighborhood`, `area_m2`, `bedrooms`, `bathrooms`, `parking`, `images`, `url`, `contact`).
  - Geographic containment within authorized Barranquilla Norte / Noroccidente sectors.
  - Valid direct portal URLs pointing to official domains (`metrocuadrado.com`, `fincaraiz.com.co`).
  - Actionable contact details: unmasked Colombian phone numbers (`+57 3XX XXXXXXX`) and WhatsApp strings.
  - Cross-portal deduplication integrity (canonical fingerprint uniqueness).
- **Requirement R2 (Interactive Local Dashboard & State Persistence)**:
  - HTTP server startup, loopback binding, and zero-error root index serving (`GET /`).
  - Static asset delivery with accurate MIME headers (`text/html`, `text/css`, `application/javascript`, `image/svg+xml`).
  - Real-time client-side filtering logic across text, neighborhood, price slider, rooms, bathrooms, and parking.
  - Price breakdown visual badges (`Canon` + `Admin` = `Total`).
  - Interest state mutation and persistence (`/api/tracking` POST and GET round-trip).
  - WhatsApp appointment deep-link generation with pre-composed query parameters.
  - Export capabilities (`/api/export?format=json` and `/api/export?format=csv`).
- **Requirement R3 (Curated Immediate Visit Dossier & Contact Sheets)**:
  - Dossier volume constraints ($10 \le N \le 15$ standout properties).
  - 100-point Multi-Factor Value Index (MFVI) calculation and quality thresholds ($\text{score} \ge 75.0$).
  - Actionable contact readiness (100% of curated properties possess direct WhatsApp links).
  - Multi-format delivery parity (`DOSSIER_VISITAS.md` vs `data/dossier_curado.json`).
  - Physical inspection checklist presence (water pressure, solar orientation, electric plant, parking slot).
  - 4-Day logistical visit itinerary (Wednesday through Saturday circuits).

### 2.2 Tier 2: Boundary & Corner Cases (Boundary Value Analysis - BVA)
Stress-tests extreme edges, numeric thresholds, and degenerate input formats:
- **Exact Ceiling Boundary**: Listing with total price exactly equal to **$2.500.000 COP** must be accepted.
- **Ceiling Breach Rejection**: Listing with total price **$2.500.001 COP** must be strictly rejected and discarded.
- **Zero Administration Fee ($0)**: Listings where administration is $0 or included in canon must be supported without arithmetic errors or division-by-zero exceptions.
- **Extreme & Missing Input Tolerance**: Listings with missing optional attributes (`stratum: null`, `parking: 0`, `images: []`) must render safe visual fallbacks without throwing JavaScript or Python runtime exceptions.
- **API Payload Robustness**:
  - Non-dictionary JSON payloads (e.g. arrays `[1, 2, 3]` or strings `"invalid"`) return HTTP 400 Bad Request.
  - Corrupted non-UTF-8 binary payloads return HTTP 400 Bad Request.
  - Empty POST bodies return HTTP 400 Bad Request.
- **Extreme Filter Bounds**: Applying impossible criteria (e.g. price ceiling $500.000 COP) displays an informative empty-state message; triggering "Reset Filters" restores the complete 172-property inventory.

### 2.3 Tier 3: Cross-Feature Interactions (Pairwise Combinations)
Validates that disparate subsystems interact coherently without state drift, data loss, or race conditions:
- **Compound Multi-Filter Combinations**: Simultaneous activation of Neighborhood + Max Price + Minimum Bedrooms + Parking Filter narrows the active selection to the exact mathematical intersection.
- **Dynamic State Persistence Under Active Filters**: Marking a property as `Favorito` or `Visita programada` while filtering maintains its status and persists it to disk without resetting the user's active filter view.
- **Dossier and Main Catalog Synchronization**: Every listing in the curated dossier is guaranteed to exist in the primary catalog with identical financial figures, URLs, and phone numbers.
- **REST API + Database Storage Synchronization**: The REST endpoint `/api/properties` returns data 100% byte-consistent with `data/inmuebles_barranquilla.json`.
- **Dual-Layer Persistence Consistency**: State saved via `/api/tracking` updates `data/user_tracking.json` atomically and is faithfully reflected in subsequent CSV/JSON exports.

### 2.4 Tier 4: Real-World Application Scenarios (End-to-End User Journeys)
Models realistic human workflows through multi-step operational journeys:
- **Scenario 1: The Young Professional Journey (Riomar / Villa Santos ≤ $2.2M)**:
  1. Opens the dashboard.
  2. Filters for 2-bedroom apartments in Riomar and Villa Santos with budget ≤ $2.2M COP.
  3. Sorts by lowest price per m² (highest space efficiency).
  4. Inspects property details and marks top 2 picks as `Favorito`.
  5. Triggers WhatsApp booking link to initiate contact.
  6. Verifies state persistence and prefilled WhatsApp query.
- **Scenario 2: The Corporate Executive Journey (Alto Prado / El Golf with Parking)**:
  1. Searches for 2-3 bedroom apartments in Tier A+ sectors (Alto Prado, El Golf) with private parking.
  2. Inspects building amenities (elevator, power backup, 24/7 security).
  3. Sets status to `Visita programada` with visit date and custom note.
  4. Cross-references property in the Curated Dossier.
  5. Verifies that custom notes and visit schedules persist across simulated page reloads.
- **Scenario 3: The Family Space Optimizer Journey (Miramar / Villa Carolina)**:
  1. Searches for 3-bedroom family housing with budget ≤ $2.3M COP.
  2. Reviews candidate cards; discards options lacking adequate ventilation or parking.
  3. Toggles "Ocultar descartados" filter to remove clutter.
  4. Realizes an error, navigates to "Descartados", and restores one property back to "Por contactar".
  5. Asserts counter pills and filesystem state reflect the recovery accurately.
- **Scenario 4: The Fast-Track Immediate Renter Journey (Dossier & 4-Day Route)**:
  1. Directly engages the Curated Visit Dossier for this week.
  2. Reviews top-ranked MFVI selections (Diamonds & Golds).
  3. Consults the 4-day logistical route (Wednesday to Saturday).
  4. Generates direct WhatsApp visit inquiries referencing official IDs.
  5. Verifies all WhatsApp links and documentation checklists are fully actionable.

---

## 3. Test Invariants & Assertion Standards

| Layer | Contract Invariant | Automated Assertion Method |
|---|---|---|
| **Price Invariant** | Total price never exceeds $2.5M COP | `assert total_price <= 2500000` |
| **Sum Invariant** | Total equals canon + admin fee | `assert total_price == canon + admin_fee` |
| **Geography Invariant** | Neighborhood strictly inside Barranquilla Norte | `assert neighborhood.lower() in NORTH_SECTORS` |
| **Contact Invariant** | Unmasked, actionable phone or WhatsApp | `assert phone.startswith("573") or phone.startswith("3")` |
| **URL Invariant** | Valid direct HTTP/HTTPS listing link | `assert url.startswith("http://") or url.startswith("https://")` |
| **Dossier Size** | Between 10 and 15 curated properties | `assert 10 <= len(dossier) <= 15` |
| **MFVI Quality** | All curated properties score $\ge 75$ pts | `assert mfvi_score >= 75.0` |
| **HTTP Invariant** | Standard endpoints return HTTP 200 | `assert response.status == 200` |
| **API Sanitation** | Corrupted inputs return HTTP 400 | `assert response.status == 400` |
| **State Persistence** | Deserialized state equals mutated state | `assert json.loads(stored_file) == expected_state` |

---

## 4. Test Execution & Reporting Harness

### 4.1 Dedicated E2E Runner
```bash
python -m unittest tests/test_e2e.py
```

### 4.2 Top-Level Master Test Runner
```bash
python run_all_tests.py
```
`run_all_tests.py` orchestrates all test suites across the repository (`test_pipeline.py`, `test_dashboard.py`, `test_dossier.py`, all adversarial suites, and `test_e2e.py`), generating a unified, color-coded executive verification report and returning exit code `0` on 100% success or `1` on any failure.

---
*Testing Infrastructure Specification certified for Milestone M-E2E.*
