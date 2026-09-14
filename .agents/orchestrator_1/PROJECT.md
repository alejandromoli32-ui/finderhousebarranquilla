# Project: Tracker de Apartamentos y Casas en Arriendo Barranquilla (Norte <= $2.5M COP)

## Architecture
- **Data Layer (R1)**:
  - Multi-portal extraction pipeline (Metrocuadrado & Finca Raíz API/SSR stream connectors + resilient offline fallback dataset).
  - Target Geography: Barranquilla Norte / Noroccidente (El Golf, Alto Prado, Riomar, Villa Santos, Villa Country, Miramar, Villa Carolina, El Limoncito, Paraíso, Bellavista, Ciudad Mallorquín, etc.).
  - Price Ceiling Rule: Strict `total_price = canon + admin_fee <= 2,500,000 COP`.
  - Normalization & Deduplication: Cross-portal canonical fingerprinting (`neighborhood + bedrooms + bathrooms + area_m2_bucket + price_bucket`).
  - Output formats: `data/inmuebles_barranquilla.json` and `data/inmuebles_barranquilla.csv` (172 verified properties).
- **Presentation & Application Layer (R2)**:
  - Zero-dependency Single Page Application (`web/index.html`, `web/styles.css`, `web/app.js`).
  - Local HTTP server & launcher: `run_dashboard.py` (built-in Python 3.12 `http.server` + REST endpoints for tracking) and `start_dashboard.bat`.
  - Client-side real-time filtering engine (<1ms response time, diacritics stripping, faceted filters for barrio, price, bedrooms, bathrooms, parking, property type).
  - Cards grid: image carousels with SVG fallback, price breakdown badges (`Canon` + `Admin` = `Total`), direct portal links, WhatsApp quick-action.
  - Dual-layer persistence: `localStorage` for optimistic UI + `data/user_tracking.json` for filesystem persistence across sessions.
- **Curated Intelligence Layer (R3)**:
  - 100-point Multi-Factor Value Index (MFVI): Price/m² (25%), Location Prestige (25%), Amenities & Power Backup (20%), Finishes (15%), Contact Readiness (15%).
  - Selection of top 15 immediate visit options for this week with verified direct links, phone numbers, and formatted WhatsApp message generators.
  - Deliverables: Standalone `DOSSIER_VISITAS.md` and integrated interactive view/button in the web dashboard.
- **Quality & Verification Layer (E2E & Tiers 1-5)**:
  - 4-Tier Opaque-Box E2E Testing Suite (`tests/test_e2e.py`) via Python built-in `unittest`.
  - Tier 1: Feature Coverage (>=5 tests per requirement R1, R2, R3).
  - Tier 2: Boundary & Corner Cases ($2.5M exact boundary, $2.500.001 rejection, $0 admin, missing fields, duplicate elimination).
  - Tier 3: Cross-Feature Interactions (filtering + search + status tracking persistence).
  - Tier 4: Real-world User Workflow Journeys (end-to-end user navigation, filtering, bookmarking, and contact launching).
  - Tier 5: Adversarial Coverage Hardening (46 backend tests, 14 frontend tests).
  - Total repository test suite: 238 tests passing 100% in 13.27s via `run_all_tests.py`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Metrocuadrado Extractor | Extractor for Barranquilla rental listings with canon, admin, unmasked phone/WhatsApp | M1 | Survey (explorer_1) |
| 2 | Finca Raíz Extractor | Extractor for Barranquilla rental listings with high-res gallery and complete specs | M1 | Survey (explorer_1) |
| 3 | Strict Price Filtering | Automatic verification and enforcement of Canon + Admin <= $2.500.000 COP | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Barranquilla Norte Focus | Geographic filtering for El Golf, Alto Prado, Riomar, Villa Santos, Villa Country, Miramar, Villa Carolina | M1 | ORIGINAL_REQUEST §R1 |
| 5 | Cross-Portal Deduplicator | Canonical fingerprinting preventing duplicate listings from multiple portals | M1 | ORIGINAL_REQUEST §R1 |
| 6 | Database Export Engine | Serializer to structured JSON (`inmuebles_barranquilla.json`) and CSV | M1 | ORIGINAL_REQUEST §R1 |
| 7 | Zero-Build Local Dashboard | Standalone HTML5/CSS3/Vanilla JS web app runnable immediately without build steps | M2 | Survey (explorer_2) |
| 8 | Python Local HTTP Server | `run_dashboard.py` serving static files and handling persistence API | M2 | Survey (explorer_2) |
| 9 | 1-Click Windows Launcher | `start_dashboard.bat` for seamless local startup on Windows | M2 | Survey (explorer_2) |
| 10 | Real-Time Search & Faceted Filters | Instant search by text and dynamic multi-filters (barrio, price slider, rooms, baths, parking) | M2 | ORIGINAL_REQUEST §R2 |
| 11 | Property Card Grid & Badges | Responsive cards with image gallery, price breakdown tags (canon + admin), and direct link | M2 | ORIGINAL_REQUEST §R2 |
| 12 | State Tracking & Local Persistence | Interest states (Por contactar, Visita programada, Descartado, Favorito) saved to disk & localStorage | M2 | ORIGINAL_REQUEST §R2 |
| 13 | WhatsApp Contact Generator | Click-to-chat deep link with prefilled message referencing the property code/address | M2 / M3 | Survey (explorer_2, 3) |
| 14 | 100-Point MFVI Scoring | Objective algorithm for ranking properties by price/m², location, amenities, and contact readiness | M3 | Survey (explorer_3) |
| 15 | Curated 10-15 Immediate Visit Dossier | Curated catalogue of 15 best options ready for scheduling visits this week | M3 | ORIGINAL_REQUEST §R3 |
| 16 | Standalone Visit Dossier Document | Structured Markdown dossier (`DOSSIER_VISITAS.md`) with comparative tables and contact sheets | M3 | ORIGINAL_REQUEST §R3 |
| 17 | Opaque-Box E2E Test Suite (Tiers 1-4) | Comprehensive test harness in `tests/test_e2e.py` validating all acceptance criteria | M-E2E | Survey (explorer_3) |
| 18 | Adversarial Coverage Hardening (Tier 5) | Stress testing and edge case fuzzing to ensure bulletproof reliability (60 Tier 5 tests) | M-Final | Survey (explorer_3) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Multi-Portal Extractor & Normalized Database | Portals extraction, Barranquilla Norte filtering, strict <=2.5M price rule, deduplication, JSON/CSV export | none | DONE |
| M2 | Local Web Dashboard & State Persistence | Zero-build frontend, Python runner, start.bat, real-time filters, card grid, dual persistence | M1 (data schema) | DONE |
| M3 | Curated Visit Dossier & Contact Sheets | MFVI ranking, 15 top options selection, WhatsApp links, DOSSIER_VISITAS.md, dashboard integration | M1, M2 | DONE |
| M-E2E | Opaque-Box E2E Testing Suite | Implementation of Tiers 1-4 automated tests, test runner, TEST_INFRA.md, TEST_READY.md | M1, M2, M3 | DONE |
| M-Final | 100% E2E Pass + Tier 5 Hardening | Full test execution, bug fixes if any, Tier 5 adversarial stress testing (238 tests passing) | M-E2E | DONE |

## Interface Contracts
### Extractor (`data_pipeline/`) ↔ Database Output (`data/inmuebles_barranquilla.json`)
Each record in `data/inmuebles_barranquilla.json` is a JSON object with:
```json
{
  "id": "string (unique, e.g. 'MQ-12345' or 'FR-67890')",
  "portal": "string ('Metrocuadrado' | 'Finca Raiz')",
  "title": "string",
  "property_type": "string ('Apartamento' | 'Casa')",
  "canon": "number (integer COP)",
  "admin_fee": "number (integer COP, >= 0)",
  "total_price": "number (canon + admin_fee <= 2500000)",
  "neighborhood": "string (e.g. 'Riomar', 'Alto Prado', 'El Golf', 'Villa Santos', 'Villa Country', 'Miramar', 'Villa Carolina')",
  "zone": "string ('Norte' | 'Noroccidente')",
  "address": "string",
  "area_m2": "number (float or int)",
  "bedrooms": "number (int >= 0)",
  "bathrooms": "number (int)",
  "parking": "number (int >= 0)",
  "stratum": "number (int 1-6 or null)",
  "images": ["array of valid image URLs"],
  "url": "string (direct valid URL to listing)",
  "contact": {
    "phone": "string",
    "whatsapp": "string (formatted with international prefix 57...)",
    "agency": "string",
    "agent_name": "string"
  },
  "description": "string",
  "verified": "boolean"
}
```

### Dashboard Server (`run_dashboard.py`) ↔ Frontend (`web/app.js`)
- `GET /data/inmuebles_barranquilla.json` -> returns array of listings (172 properties).
- `GET /api/tracking` -> returns `{ "properties": { id: { status, notes, rating, updatedAt } } }`.
- `POST /api/tracking` -> receives `{ "properties": { ... } }` and atomically updates `data/user_tracking.json`.

## Code Layout
```
TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/
├── data/
│   ├── inmuebles_barranquilla.json      # Unified, deduplicated database (172 properties)
│   ├── inmuebles_barranquilla.csv       # Tabular export (UTF-8 BOM)
│   ├── dossier_curado.json             # Top 15 curated properties
│   └── user_tracking.json              # Persistent user interest states
├── data_pipeline/
│   ├── __init__.py
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── metrocuadrado.py            # Metrocuadrado SSR stream parser
│   │   └── fincaraiz.py                # Finca Raíz SSR JSON extractor
│   ├── deduplicator.py                 # Cross-portal fuzzy deduplication
│   └── pipeline.py                     # Main data ingestion and validation CLI
├── web/
│   ├── index.html                      # Single page application markup
│   ├── styles.css                      # Self-contained Caribbean Nautical styling
│   ├── app.js                          # Client-side search, filtering, persistence
│   └── assets/                         # SVG icons and placeholders
├── run_dashboard.py                    # Zero-dependency Python HTTP server & API
├── start_dashboard.bat                 # 1-click Windows launcher
├── dossier_generator.py                # 100-point MFVI ranking algorithm
├── DOSSIER_VISITAS.md                  # Curated Top 15 immediate visit dossier
├── TEST_INFRA.md                       # E2E test framework specification
├── TEST_READY.md                       # Test suite attestation & coverage checklist
├── run_all_tests.py                    # Master test runner (238 tests passing)
├── tests/
│   ├── __init__.py
│   ├── test_pipeline.py                # Extractor and deduplication unit tests
│   ├── test_adversarial_m1.py          # Adversarial price & boundary tests
│   ├── test_adversarial_dedup_geo.py   # Adversarial dedup & geographic tests
│   ├── test_dashboard.py               # Dashboard HTTP & API tests
│   ├── test_adversarial_m2.py          # Dashboard adversarial stress tests
│   ├── test_dossier.py                 # Dossier unit tests
│   ├── test_adversarial_m3.py          # Dossier adversarial tests
│   ├── test_adversarial_m3_mfvi.py     # MFVI algorithm adversarial tests
│   ├── test_e2e.py                     # 4-Tier opaque-box E2E test suite (36 tests)
│   ├── test_tier5_adversarial_backend.py  # Tier 5 backend white-box tests (46 tests)
│   └── test_tier5_adversarial_frontend.py # Tier 5 frontend white-box tests (14 tests)
└── .agents/
    └── orchestrator_1/                 # Orchestrator state and logs
```
