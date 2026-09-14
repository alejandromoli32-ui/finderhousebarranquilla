# Technical Survey & Specification: Curated Immediate Visit Dossier (R3) & Opaque-Box E2E Testing Strategy (Tiers 1-4)

**Agent**: `explorer_survey_3`  
**Milestone**: M0 — Technical Exploration & Architecture Survey  
**Date**: 2026-09-13  
**Status**: Complete Technical Specification  
**Parent**: `orchestrator_1` (Conversation ID: `78e1bffd-c00b-4edf-9b66-26fc5574a726`)

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Curated Immediate Visit Dossier (Requirement R3)](#2-curated-immediate-visit-dossier-requirement-r3)
   - [2.1 Barranquilla Norte Real Estate Context](#21-barranquilla-norte-real-estate-context)
   - [2.2 Candidate Selection Methodology (10-15 Target)](#22-candidate-selection-methodology-10-15-target)
   - [2.3 Multi-Factor Value Index (MFVI) Scoring Model](#23-multi-factor-value-index-mfvi-scoring-model)
   - [2.4 Content Architecture & Section Structure](#24-content-architecture--section-structure)
   - [2.5 Delivery Formats Specification](#25-delivery-formats-specification)
   - [2.6 Operational Visit Protocol for Barranquilla](#26-operational-visit-protocol-for-barranquilla)
3. [Opaque-Box E2E Testing Strategy (Tiers 1 to 4)](#3-opaque-box-e2e-testing-strategy-tiers-1-to-4)
   - [3.1 Opaque-Box Testing Philosophy & Host Environment](#31-opaque-box-testing-philosophy--host-environment)
   - [3.2 Tier 1: Feature Coverage Test Suite (>=5 per Feature)](#32-tier-1-feature-coverage-test-suite-5-per-feature)
   - [3.3 Tier 2: Boundary & Corner Case Suite](#33-tier-2-boundary--corner-case-suite)
   - [3.4 Tier 3: Cross-Feature Combination Suite](#34-tier-3-cross-feature-combination-suite)
   - [3.5 Tier 4: Real-World User Scenario Journeys](#35-tier-4-real-world-user-scenario-journeys)
   - [3.6 Test Runner Architecture, Assertions & Pass/Fail Semantics](#36-test-runner-architecture-assertions--passfail-semantics)
4. [Synthesis, Downstream Dependencies & Implementation Roadmap](#4-synthesis-downstream-dependencies--implementation-roadmap)

---

# 1. Executive Summary

This document establishes the authoritative technical blueprint for two critical pillars of the Barranquilla Real Estate Tracker and Dashboard:

1. **Requirement R3 (Curated Immediate Visit Dossier)**: A rigorously selected, verified catalogue of 10 to 15 top-tier rental properties in Barranquilla Norte (El Golf, Alto Prado, Riomar, Villa Santos, Villa Country, Miramar, Villa Carolina, etc.) strictly respecting the total price ceiling of **$2.500.000 COP/month (Canon + Administración)**. It introduces the **Multi-Factor Value Index (MFVI)** to score properties across price efficiency, location prestige, tropical amenities, physical finishes, and immediate contact readiness.
2. **Opaque-Box E2E Testing Strategy (Tiers 1 to 4)**: A comprehensive, black-box verification harness ensuring end-to-end correctness across data integrity (R1), dashboard responsiveness and persistence (R2), and curated dossier delivery (R3). It defines 20+ feature coverage tests (Tier 1), 8 boundary and edge tests (Tier 2), 6 cross-feature interaction suites (Tier 3), and 4 realistic user journeys (Tier 4), complete with zero-dependency native execution semantics for Windows environments.

---

# 2. Curated Immediate Visit Dossier (Requirement R3)

## 2.1 Barranquilla Norte Real Estate Context

Searching for rental housing in Barranquilla Norte within a budget of **$2.500.000 COP total** is one of the most competitive segments in the Atlantic coastal market. 

### Key Geographic Sectors & Estrato Tiers:
- **Tier 1 (Core Premium / Classic Norte — Estrato 5 & 6)**:
  - *Barrios*: El Golf, Alto Prado, Riomar, Villa Country.
  - *Characteristics*: Highly walkable, tree-lined streets, proximity to CC Viva Barranquilla, CC Buenavista, Country Club, fine dining (Carrera 51B, 53, Calle 79, 82, 84).
  - *Market Dynamics at <= $2.5M*: Generally rents 1BR to 2BR apartments (50–75 m²), or older classic apartments (75–95 m²). Administration fees typically range from $350.000 to $600.000 COP, requiring a canon of $1.900.000 to $2.150.000 COP.
- **Tier 2 (Modern Residential / Upper Expansion — Estrato 4 & 5)**:
  - *Barrios*: Villa Santos, Altos de Riomar, Buenavista perimeter, Altos del Limón.
  - *Characteristics*: Modern mid-to-high-rise residential towers, excellent breezes due to elevation, close to Mall Plaza and Clinica Portoazul.
  - *Market Dynamics at <= $2.5M*: Generous 2BR to 3BR units (70–105 m²), usually in buildings under 15 years old with full club amenities (pool, gym, 24/7 security). Admin fees: $250.000 to $450.000 COP.
- **Tier 3 (High-Amenity Family & Emerging Corridors — Estrato 4 & 5)**:
  - *Barrios*: Miramar, Villa Carolina, Paraíso, Andalucía, Ciudad Mallorquín (corredor universitario / Puerto Colombia border).
  - *Characteristics*: Master-planned family residential developments, extensive public parks (Parque Villa Carolina, Parque Miramar), newer developments.
  - *Market Dynamics at <= $2.5M*: 3BR apartments (75–110 m²) and select townhouses/casas. Admin fees: $180.000 to $320.000 COP. Exceptional space-per-peso ratio.

### Common Market Pitfalls in Barranquilla Rental Search:
1. **The Administration Surprise**: Portals often advertise canon alone ($2.200.000) while burying administration fees ($550.000) in the description text, causing total monthly outlay ($2.750.000) to exceed the budget.
2. **Ghost Listings & Stale Publications**: Real estate agencies often leave rented properties active for lead capture.
3. **Contact Friction**: Listings lacking direct WhatsApp links or mobile phone numbers require filling slow web forms that have a response time of 3–5 days, ruining the ability to "visit this week".
4. **Caribbean Climate Requirements**: In Barranquilla, properties lacking covered parking (ruinous to vehicles under tropical sun) or without adequate electrical backup (planta eléctrica) or cross-ventilation present severe habitability deficits.

The Curated Dossier acts as an expert curation filter that eliminates all these frictions.

---

## 2.2 Candidate Selection Methodology (10-15 Target)

To produce an elite, verified selection of 10 to 15 properties, the system follows a 4-stage funnel:

```
[ All Scraped/Aggregated Records in DB ] (e.g. 100-300 listings)
                   │
                   ▼ Stage 1: Hard Binary Filters
[ Validated Candidate Pool ] (Strict <= $2.5M COP, North Sector, Active Link, Photos, Contact)
                   │
                   ▼ Stage 2: Multi-Factor Value Index (MFVI) Scoring
[ Scored Candidate Pool (0 - 100 Points) ]
                   │
                   ▼ Stage 3: Diversity & Typology Quota Balancing
[ Balanced Top Candidates ] (El Golf/Alto Prado + Villa Santos + Miramar/Villa Carolina)
                   │
                   ▼ Stage 4: Verification & Final Dossier Generation
[ Final 10-15 Curated Properties Ready for Immediate Booking ]
```

### Stage 1: Hard Binary Filters (Pass/Fail)
A listing is immediately rejected from dossier consideration if it fails any of these:
1. **Total Price Violation**: `Canon + Admin > $2.500.000 COP`.
2. **Geographic Invalidation**: Property located outside designated North/Noroccidente perimeter.
3. **Image Deficiency**: Fewer than 3 high-resolution photos available.
4. **Contact Void**: No telephone, WhatsApp, or identifiable agency contact.
5. **URL Invalidation**: Broken link, redirected listing, or expired publication.

### Stage 2: Algorithmic Scoring (MFVI)
All surviving candidates are evaluated by the Multi-Factor Value Index (Section 2.3).

### Stage 3: Diversity & Typology Quota Balancing
To provide real-world utility for different tenant profiles, the selection enforces distribution quotas across the 10-15 finalists:
- **Typology Spread**:
  - At least 3 Executive / Compact 1-2 Bedroom units (ideal for singles/corporate relocators in Alto Prado/El Golf).
  - At least 5 Mid-Size 2-3 Bedroom units (ideal for couples or home-office workers in Villa Santos/Riomar).
  - At least 3 Spacious 3 Bedroom units or houses (ideal for families in Miramar/Villa Carolina).
- **Geographic Spread**:
  - Maximum 5 properties from any single neighborhood to guarantee sector variety.

### Stage 4: Contact Readiness Verification
Finalists must have an active phone number capable of receiving WhatsApp inquiries, verified with a generated click-to-chat deep link.

---

## 2.3 Multi-Factor Value Index (MFVI) Scoring Model

The **Multi-Factor Value Index (MFVI)** evaluates each candidate property on a **0 to 100 point scale** across 5 distinct dimensions:

$$\text{MFVI Total} = S_{\text{price\_m2}} + S_{\text{location}} + S_{\text{amenities}} + S_{\text{finishes}} + S_{\text{contact}}$$

| Dimension | Weight | Max Points | Evaluation Factors |
|---|:---:|:---:|---|
| **1. Price/m² Efficiency** | 25% | **25 pts** | Cost per square meter relative to Barranquilla Norte benchmarks |
| **2. Location Prestige & Safety** | 25% | **25 pts** | Sector desirability, estrato, walkability, safety, services |
| **3. Amenities & Tropical Resilience** | 20% | **20 pts** | Covered parking, elevator, power generator, pool/gym, 24/7 security |
| **4. Physical Condition & Finishes** | 15% | **15 pts** | Modern integral kitchen, ventilation/balcony, bathroom ratio |
| **5. Contact Readiness & Agility** | 15% | **15 pts** | Direct WhatsApp link, mobile number, agency/broker responsiveness |
| **TOTAL** | **100%** | **100 pts** | **Comprehensive Value Score** |

### Detailed Scoring Breakdown:

#### 1. Price per Square Meter Efficiency ($S_{\text{price\_m2}}$ — Max 25 pts)
Unit cost is calculated as: $\text{Cost/m}^2 = \frac{\text{Total Price (Canon + Admin)}}{\text{Area (m}^2\text{)}}$.
- $\text{Cost/m}^2 < \$28.000\text{ COP/m}^2$: **25 points** *(Exceptional space-per-peso efficiency)*
- $\$28.000 \le \text{Cost/m}^2 \le \$33.000\text{ COP/m}^2$: **21 points** *(Highly favorable market value)*
- $\$33.001 \le \text{Cost/m}^2 \le \$38.000\text{ COP/m}^2$: **17 points** *(Balanced market average for Norte)*
- $\$38.001 \le \text{Cost/m}^2 \le \$44.000\text{ COP/m}^2$: **13 points** *(Standard for compact premium units)*
- $\text{Cost/m}^2 > \$44.000\text{ COP/m}^2$: **8 points** *(High premium per m²)*

#### 2. Location Prestige & Walkability ($S_{\text{location}}$ — Max 25 pts)
- **Tier A+ (25 pts)**: El Golf, Alto Prado, Riomar, Villa Country. (Estrato 5-6, maximum prestige, walkable to retail hubs, high security).
- **Tier A (22 pts)**: Villa Santos, Altos de Riomar, Buenavista area. (Estrato 5-6, top modern residential, close to CC Buenavista/Mall Plaza).
- **Tier B+ (18 pts)**: Miramar, Villa Carolina, Paraíso, Andalucía, Altos del Limón. (Estrato 4-5, high green space, excellent family living).
- **Tier B (14 pts)**: Other designated Noroccidente zones (Ciudad Mallorquín, San Vicente, Betania Norte).

#### 3. Amenities & Tropical Infrastructure ($S_{\text{amenities}}$ — Max 20 pts)
- **Covered Parking (Parqueadero Privado Cubierto)**: **5 pts** *(Critical in Barranquilla to protect against tropical sun and torrential rains; uncovered gets 2 pts, none gets 0 pts)*.
- **Elevator & Full Electrical Backup (Planta Eléctrica)**: **5 pts** *(Planta con suplencia total o parcial para zonas comunes y nevera/luces esenciales)*.
- **Social & Wellness Amenities**: **5 pts** *(Swimming pool, equipped gym, or social lounge/terrace)*.
- **24/7 Security & Concierge (Portería)**: **5 pts** *(Controlled access, intercom, CCTV)*.

#### 4. Physical Finishes & Habitability ($S_{\text{finishes}}$ — Max 15 pts)
- **Integral Modern Kitchen (Cocina Integral)**: **6 pts** *(Granite/quartz counters, built-in stove/extractor)*.
- **Natural Ventilation & Balcony (Brisa/Sombra)**: **5 pts** *(Balcony or high floor with north/shadow orientation, reducing air-conditioning cooling expenses)*.
- **Adequate Bathrooms**: **4 pts** *(2+ full bathrooms for 2-3 bedroom units; 1 full bath for studio/1BR)*.

#### 5. Contact Readiness & Booking Agility ($S_{\text{contact}}$ — Max 15 pts)
- **Direct Mobile Phone with WhatsApp Active**: **7 pts** *(Instant messaging availability)*.
- **Prefilled WhatsApp Deep Link Available**: **4 pts** *(One-click direct dispatch with property reference)*.
- **Verified Listing Code & Direct Landlord/Agency Identification**: **4 pts** *(Eliminates intermediary delay)*.

### Quality Badging Tiers:
- **90 – 100 Points**: 🏆 **Selección Diamante (Priority #1)** — Unmatched value, immediate visit strongly urged.
- **80 – 89 Points**: 🌟 **Selección Oro (High Value)** — Excellent balance of location and space.
- **75 – 79 Points**: ✨ **Selección Plata (Approved Contender)** — Solid property meeting all criteria.
- **< 75 Points**: Excluded from the Curated Dossier (retained in general database).

---

## 2.4 Content Architecture & Section Structure

The Curated Immediate Visit Dossier is organized into 4 logical sections:

### Section I: Executive Summary & Market Snapshot
- **Inventory Overview**: Total properties in database vs. properties curated into the dossier (e.g. "12 Outstanding Properties Selected from 185 Evaluated").
- **Financial Metrics**:
  - Minimum total price, maximum total price, median total price (e.g. median: $2.250.000 COP).
  - Average administration fee (e.g. $340.000 COP) and average canon (e.g. $1.910.000 COP).
  - Average price per square meter (e.g. $30.400 COP/m²).
- **Fast-Track Recommendations**:
  - *Top Executive Pick*: Best 1-2BR in El Golf/Alto Prado.
  - *Top Family Pick*: Best 3BR in Villa Santos/Miramar.
  - *Best Value-per-m²*: Highest square footage per peso spent.

### Section II: Comparative Master Decision Table
A dense, sortable matrix enabling rapid multi-attribute comparison:

| Rank | Ref ID | Barrio | Tipo | Área (m²) | Canon | Admin | Total Mes | $/m² | Hab | Bañ | Pq | Score | Acción Inmediata |
|:---:|:---:|:---|:---:|:---:|---:|---:|---:|---:|:---:|:---:|:---:|:---:|:---:|
| #1 | BQ-104 | Alto Prado | Apto | 82 | $1.950.000 | $380.000 | **$2.330.000** | $28.414 | 2 | 2 | 1 Cub | **95 pts** | [📲 WhatsApp](https://wa.me/573001234567?text=...) |
| #2 | BQ-118 | Villa Santos | Apto | 96 | $1.900.000 | $390.000 | **$2.290.000** | $23.854 | 3 | 2 | 1 Cub | **93 pts** | [📲 WhatsApp](https://wa.me/573109876543?text=...) |
| #3 | BQ-142 | El Golf | Apto | 68 | $2.050.000 | $420.000 | **$2.470.000** | $36.323 | 2 | 2 | 1 Cub | **91 pts** | [📲 WhatsApp](https://wa.me/573155551234?text=...) |

### Section III: Detailed Property Factsheets (Fichas Técnicas)
Each of the 10-15 properties features an individual comprehensive factsheet:
1. **Header**: Rank Badge (`#1`), Title, Neighborhood, Score Badge (`95/100 - Selección Diamante`).
2. **Visual Showcase**: Primary featured photo + gallery preview strip.
3. **Financial Breakdown**:
   - Canon de arrendamiento: `$X.XXX.XXX COP`
   - Valor de administración: `$XXX.XXX COP`
   - **Costo Total Mensual**: `$X.XXX.XXX COP` *(Destacado)*
   - Costo unitario: `$XX.XXX COP / m²`
4. **Physical Specifications**:
   - Tipo de Inmueble (Apartamento / Casa)
   - Área privada: `XX m²`
   - Distribución: `X Habitaciones | X Baños | X Parqueaderos (Cubierto/Descubierto)`
   - Estrato socioeconómico: `Estrato 4 / 5 / 6`
   - Piso y orientación: `Piso X (Sombra / Brisa)`
5. **Building & Interior Amenities**: Checklist badges for Piscina, Gimnasio, Planta Eléctrica, Ascensor, Vigilancia 24h, Balcón, Cocina Integral, Gas Natural.
6. **Curator's Value Thesis ("¿Por qué fue seleccionado?")**:
   - 2-3 sentences explaining the exceptional price/quality advantage.
7. **Physical Visit Inspection Checklist ("Puntos clave a revisar en la visita")**:
   - Specific items for the prospective tenant to verify on-site (e.g. check water pressure in showers, confirm if electric plant powers air conditioners or only lighting, verify parking slot maneuverability).
8. **Contact & Instant Scheduling Action Bar**:
   - Nombre de contacto / Inmobiliaria.
   - Teléfono directo.
   - **One-Click WhatsApp Booking Button** (Deep link with pre-composed appointment message).
   - Enlace directo a la publicación original en el portal.

### Section IV: Operational Visit Logistics & Rental Application Protocol
Practical guide tailored to Barranquilla's rental market requirements:
- Insurers operating in Barranquilla (*Aseguradora El Libertador*, *Seguros Bolívar*, *Sura*, *FianzaCrédito*).
- Required documentation for tenant and co-debtor (Cédula, 3 últimos desprendibles de nómina, 3 últimos extractos bancarios, certificado laboral).
- Income formula: Tenant must demonstrate income equal to $2.5 \times \text{Canon}$, co-debtor with real estate or equivalent income.

---

## 2.5 Delivery Formats Specification

The Curated Dossier must be delivered in **3 synchronized formats**:

### Format 1: Standalone Markdown Dossier (`dossier_visitas_inmediatas.md`)
- Universal, readable in any editor, terminal, VSCode, or GitHub.
- Self-contained with markdown tables, callout blocks (`> 💡 **Nota del Curador**`), markdown image links, and hyperlinked WhatsApp URLs.
- Stored directly in the project root or documentation directory for instant user access.

### Format 2: Interactive Web Dashboard View
- A dedicated **"Dossier de Visitas Inmediatas"** tab/modal inside the local dashboard.
- Interactive cards styled with Gold/Silver/Diamond badges.
- Quick filter buttons: "Todos", "1-2 Alcobas (Ejecutivos)", "3 Alcobas (Familias)", "El Golf / Alto Prado".
- "Copiar mensaje de WhatsApp" button (copies formatted appointment inquiry text to clipboard).
- "Abrir WhatsApp Web" button.

### Format 3: Exportable Print-Ready HTML/PDF (`dossier_visitas_inmediatas.html`)
- Standalone HTML file with embedded responsive CSS, no external network dependencies.
- Integrated `@media print` rules:
  ```css
  @media print {
    body { font-size: 11pt; color: #000; background: #fff; }
    .no-print, .action-buttons { display: none !important; }
    .property-card { page-break-inside: avoid; border: 1px solid #ccc; margin-bottom: 20px; }
    .page-break { page-break-before: always; }
  }
  ```
- Includes a floating **"🖨️ Descargar como PDF / Imprimir"** button calling `window.print()`.
- Generates clean, publication-grade multi-page PDFs suitable for sharing with partners or printing for physical visits.

---

## 2.6 Operational Visit Protocol for Barranquilla

To enable "immediate visits this week", the WhatsApp integration must generate a standardized, polite, and information-rich initial message:

### WhatsApp Deep-Link Format:
```
https://wa.me/57[PHONE]?text=[ENCODED_MESSAGE]
```

### Message Template:
> *"Hola [Nombre Contacto/Inmobiliaria], cordial saludo. Vi su publicación del [Tipo Inmueble] en [Barrio] (Ref: [Listing ID/Título] por $[Total] COP con administración). Tengo interés serio en visitarlo físicamente esta semana. ¿Qué días y horarios tienen disponibilidad para coordinar la visita? Quedo atento a su respuesta, muchas gracias."*

This immediate framing establishes high buyer intent, references the exact listing ID, and prompts direct scheduling availability.

---

# 3. Opaque-Box E2E Testing Strategy (Tiers 1 to 4)

## 3.1 Opaque-Box Testing Philosophy & Host Environment

### Philosophy:
- **Opaque-Box (Black-Box) Principle**: The test runner interacts strictly with the system's observable public boundaries:
  1. Data files (`properties.json`, database stores).
  2. HTTP servers / local web dashboard DOM output.
  3. Generated export files (`dossier_visitas_inmediatas.md`, `dossier_visitas_inmediatas.html`).
  4. Local browser storage (`localStorage` state).
- **Zero-Internal Mocking**: Tests do not mock internal JavaScript functions or Python classes. They supply inputs and assert end-to-end outputs.

### Host Environment Reality & Execution Strategy:
- **Operating System**: Windows host.
- **PowerShell Constraint**: Windows ExecutionPolicy may block `.ps1` wrapper scripts (e.g. `npx.ps1`, `pytest.ps1`).
- **Solution — Dual Zero-Dependency Test Runners**:
  1. **Python Native Runner (`python -m unittest tests/run_e2e_suite.py`)**: Built entirely on Python 3.12's standard library (`unittest`, `json`, `urllib`, `re`, `pathlib`). Requires zero external pip packages.
  2. **Node.js Native Runner (`node --test tests/e2e/*.test.js`)**: Built on Node 24's native `node:test` and `node:assert/strict` modules. Runs directly via `node` without requiring `npx` or npm scripts.

---

## 3.2 Tier 1: Feature Coverage Test Suite (>=5 per Feature)

Tier 1 verifies that every individual capability specified in Requirements R1, R2, and R3 operates in full conformance with its contract.

```
Total Tier 1 Tests: 18 Automated Tests (6 for R1, 6 for R2, 6 for R3)
Pass Threshold: 100% (18/18 PASS)
```

### Feature R1: Base de Datos y Extracción Multi-Portal (Barranquilla Norte)

| Test ID | Test Case Name | Target Contract / Invariant | Automated Assertion |
|---|---|---|---|
| **R1-1** | `test_r1_schema_conformance` | All records adhere to the required JSON schema | Every record contains `id`, `title`, `property_type`, `canon_price`, `admin_price`, `total_price`, `neighborhood`, `area_m2`, `bedrooms`, `bathrooms`, `parking`, `images`, `url`, `contact`. All types strictly validated. |
| **R1-2** | `test_r1_price_ceiling_strict` | Strict budget ceiling <= $2.500.000 COP | $\forall p \in \text{DB}: p.\text{total\_price} \le 2.500.000$ and $p.\text{total\_price} == p.\text{canon\_price} + p.\text{admin\_price}$. |
| **R1-3** | `test_r1_geography_north_only` | All records within Barranquilla Norte polygon | $\forall p \in \text{DB}: p.\text{neighborhood} \in \text{BARRANQUILLA\_NORTE\_SECTORS}$. Rejects non-north listings. |
| **R1-4** | `test_r1_cross_portal_deduplication` | No duplicate listings across portals | Given duplicate listings from Metrocuadrado and Finca Raíz with matching address/area/canon, database merges to 1 unique record. |
| **R1-5** | `test_r1_valid_portal_urls` | All listing URLs are direct, valid HTTP/HTTPS | Every `url` matches `^https?:\/\/(www\.)?(fincaraiz|metrocuadrado|ciencuadras|mercadolibre)\.com.*` and contains valid path. |
| **R1-6** | `test_r1_contact_data_presence` | Actionable contact info present on every listing | Every record has `contact.phone` or `contact.whatsapp` or valid `contact.agency` string; none are null or empty. |

### Feature R2: Buscador y Dashboard Web Interactivo Local

| Test ID | Test Case Name | Target Contract / Invariant | Automated Assertion |
|---|---|---|---|
| **R2-1** | `test_r2_dashboard_boot_and_render` | Web dashboard loads and initializes UI | DOM renders container `#property-grid`, displays total count badge matching DB length, console has 0 fatal JS errors. |
| **R2-2** | `test_r2_realtime_text_search` | Real-time text search updates grid instantly | Typing "Alto Prado" into `#search-input` filters DOM cards to only those containing "Alto Prado" in title or neighborhood; latency < 50ms. |
| **R2-3** | `test_r2_dynamic_multicriteria_filter` | Compound filtering (Price + Bed + Parking) | Applying slider `maxPrice=2200000`, dropdown `bedrooms>=3`, checkbox `hasParking=true` renders cards matching all 3 conditions. |
| **R2-4** | `test_r2_pricing_breakdown_badges` | Transparent breakdown of canon + admin | Every rendered card visibly displays `.badge-canon`, `.badge-admin`, and `.badge-total` formatted in COP currency. |
| **R2-5** | `test_r2_interest_state_mutation` | User can update interest status | Clicking `.btn-mark-visita` on card transitions status badge to "Visita programada" and updates status counters. |
| **R2-6** | `test_r2_persistence_localstorage` | Statuses persist across page reload | Storing status changes into `localStorage`, simulating reload, asserts cards reload with identical statuses and counters. |

### Feature R3: Dossier Curado de Opciones Inmediatas

| Test ID | Test Case Name | Target Contract / Invariant | Automated Assertion |
|---|---|---|---|
| **R3-1** | `test_r3_dossier_count_bounds` | Dossier contains 10 to 15 standout properties | $10 \le \text{len}(\text{dossier\_properties}) \le 15$. |
| **R3-2** | `test_r3_dossier_score_threshold` | Quality threshold enforced for all entries | $\forall p \in \text{Dossier}: \text{MFVI\_Score}(p) \ge 75.0$ and $p.\text{total\_price} \le 2.500.000$. |
| **R3-3** | `test_r3_dossier_contact_completeness` | 100% of dossier entries have direct contact | $\forall p \in \text{Dossier}: p.\text{contact}.\text{phone} \ne \text{null}$ and $p.\text{contact}.\text{whatsapp} \ne \text{null}$. |
| **R3-4** | `test_r3_whatsapp_deeplink_validity` | Valid WhatsApp click-to-chat links | Every dossier link matches `https://wa.me/57[0-9]{10}\?text=.*` and decoded query contains property title/ref. |
| **R3-5** | `test_r3_dossier_multiformat_parity` | Markdown, Dashboard, and HTML formats match | Property IDs in `dossier_visitas_inmediatas.md` match IDs in dashboard dossier view and `dossier_visitas_inmediatas.html`. |
| **R3-6** | `test_r3_inspection_guide_presence` | Actionable visit checklist present per card | Every dossier factsheet includes "Puntos a verificar en la visita" with at least 3 concrete inspection points. |

---

## 3.3 Tier 2: Boundary & Corner Case Suite

Tier 2 stress-tests system limits, edge values, and abnormal inputs to ensure graceful resilience:

| Test ID | Scenario Description | Input Value | Expected System Behavior | Assertion Criteria |
|---|---|---|---|---|
| **T2-1** | **Exact Price Ceiling Boundary** | Total = $2.500.000 COP (Canon $2.100.000 + Admin $400.000) | **Accepted**. Valid listing eligible for DB and Dossier. | Record accepted without warning; `total_price == 2500000`. |
| **T2-2** | **Strict Rejection Above Ceiling** | Total = $2.500.001 COP (Canon $2.100.000 + Admin $400.001) | **Rejected**. Excluded from database and dossier. | Extractor/validator drops record; log registers ceiling breach. |
| **T2-3** | **Zero Administration Fee ($0)** | Admin = $0 (or "Incluida" in listing) | **Accepted**. Total price equals Canon price ($2.300.000). | `admin_price == 0`, `total_price == canon_price`, UI displays "Admin: $0 (Incluida)". No division by zero. |
| **T2-4** | **Missing Optional Fields** | `parking: null`, `floor: null`, `images: []` | **Handled Gracefully**. Default fallbacks applied. | UI displays placeholder image ("Sin foto disponible"); parking badge displays "Consultar"; no crash. |
| **T2-5** | **Malformed & Malicious URLs** | `javascript:alert(1)`, `ftp://portal.co`, empty `""` | **Sanitized / Rejected**. | URL validator rejects non-HTTP(S) schemas; sanitized to prevent XSS. |
| **T2-6** | **Fuzzy Duplicate Detection** | Two portal listings with identical address & area, slightly different titles | **Deduplicated**. Merged into 1 record with multiple source links. | Unified DB count increments by 1, not 2; sources array contains both portal names. |
| **T2-7** | **Extreme Physical Dimensions** | Micro-studio (18 m² at $1.8M) vs Large house (280 m² at $2.4M) | **Scored Without Overflow**. | Price/m² computed accurately ($100k/m² and $8.5k/m²); no numeric clipping or NaN. |
| **T2-8** | **Currency String Normalization** | `"$ 2.450.000"`, `"COP 2450000"`, `"2.450.000,00"` | **Normalized**. All parsed to integer `2450000`. | All formatted strings convert to integer `2450000` with 100% consistency. |

---

## 3.4 Tier 3: Cross-Feature Combination Suite

Tier 3 tests the interaction of multiple system features operating simultaneously:

### Combination Test 3-1: Compound Multi-Filter + Real-Time Search
- **Action**: User enters search term `"Villa Santos"` + sets Price Slider to max `$2.200.000 COP` + checks `Habitaciones >= 3` + checks `Parqueadero: Sí`.
- **Expected Outcome**: The property grid renders ONLY records satisfying ALL four constraints simultaneously.
- **Assertion**: $\forall \text{card} \in \text{DOM}: \text{card}.\text{barrio} == \text{"Villa Santos"} \land \text{card}.\text{total} \le 2200000 \land \text{card}.\text{hab} \ge 3 \land \text{card}.\text{pq} \ge 1$.

### Combination Test 3-2: Filter Interaction with Interest Status Filter
- **Action**: User selects tab `"Favoritos"` (which currently contains 4 properties) and then types `"Alto Prado"` into the search box.
- **Expected Outcome**: Only favorites located in Alto Prado remain visible.
- **Assertion**: Visible count equals intersection of `status == "Favorito"` and `barrio == "Alto Prado"`.

### Combination Test 3-3: Dynamic Status Mutation Under Active Tab
- **Action**: User is viewing the `"Por contactar"` tab (30 items). User clicks "Programar Visita" on card #5.
- **Expected Outcome**: Card #5 immediately transitions out of the "Por contactar" view; the counter for "Por contactar" drops to 29; the counter for "Visitas Programadas" increases to 1.
- **Assertion**: Zero full-page reload occurs; state and badge counters update instantly in the DOM.

### Combination Test 3-4: Dossier & Main Catalog State Synchronization
- **Action**: A property listed in the Curated Dossier is marked as `"Visita Programada"` inside the Dossier view.
- **Expected Outcome**: Navigating back to the main catalog view shows the identical property with its `"Visita Programada"` badge active.
- **Assertion**: Shared state model guarantees single source of truth across views.

### Combination Test 3-5: Full Session Persistence Lifecycle
- **Action**: User modifies 6 items: marks 3 as Favoritos, 2 as Visitas Programadas, 1 as Descartado, and writes a personal note: `"Llamar lunes a las 9am"`. User reloads page or closes/reopens browser.
- **Expected Outcome**: All 6 modifications, badges, custom notes, and counter pills are restored with 100% fidelity.
- **Assertion**: Deserialized `localStorage` state matches the pre-reload snapshot exactly.

### Combination Test 3-6: Filter Clearing & Zero-State Recovery
- **Action**: User applies an impossible filter (e.g. Barrio `"El Golf"`, Max Price `$800.000 COP`, `5 Habitaciones`).
- **Expected Outcome**: Grid displays an informative zero-state message ("No se encontraron inmuebles con estos criterios") with a "Limpiar Filtros" button. Clicking the button restores full inventory.
- **Assertion**: Zero JavaScript exceptions; full catalog re-renders cleanly.

---

## 3.5 Tier 4: Real-World User Scenario Journeys

Tier 4 tests model complete end-to-end human workflows from start to finish:

### Scenario 4-1: "The Executive Relocator Journey"
1. **User Goal**: Executive relocating to Barranquilla needs a modern 1-2 bedroom apartment in El Golf or Alto Prado with parking, budget up to $2.5M COP total.
2. **Execution Steps**:
   - User launches local dashboard.
   - Clicks neighborhood quick-pill `"El Golf"`.
   - Selects bedroom range `1 - 2`.
   - Inspects top 3 candidate cards.
   - Clicks "Ver fotos" on top-ranked card (`Ref: BQ-104`, Alto Prado, 82m², $2.330.000 COP total).
   - Marks status as `"Visita programada"`.
   - Clicks `"Agendar por WhatsApp"` button.
3. **Verification Points**:
   - WhatsApp URL opens with prefilled text referencing `BQ-104` and asking for Saturday visit hours.
   - Card status badge updates to "Visita programada".
   - Counter for scheduled visits increments by 1.

### Scenario 4-2: "The Family Budget & Space Optimizer Journey"
1. **User Goal**: Family searching for 3 bedrooms in Villa Santos or Miramar, strictly prioritizing maximum space for a total outlay under $2.300.000 COP.
2. **Execution Steps**:
   - User opens dashboard.
   - Sets Max Price slider to `$2.300.000 COP`.
   - Sets Minimum Bedrooms to `3`.
   - Checks `"Parqueadero incluido"`.
   - Selects sort order: `"Menor precio por m² (Mayor espacio)"`.
   - Examines the top 4 results.
   - Flags 3 finalists as `"Favorito"`.
   - Switches view to `"Solo Favoritos"` tab to compare side-by-side.
   - Enters note on property #1: `"Cerca al parque Miramar, zona social con piscina"`.
3. **Verification Points**:
   - All 3 favorites have `area_m2 >= 85`, `bedrooms >= 3`, `total_price <= 2300000`.
   - Favoritos tab displays exactly 3 cards.
   - Personal note persists and displays on card #1.

### Scenario 4-3: "The Curated Dossier Fast-Track Journey"
1. **User Goal**: Busy doctor wants immediate, pre-vetted recommendations to visit this week without manually searching hundreds of listings.
2. **Execution Steps**:
   - User opens dashboard, clicks prominent header banner: `"Ver Dossier de Visitas Inmediatas Esta Semana"`.
   - Reads Executive Summary showing 12 curated options.
   - Sorts comparative master table by `Score MFVI`.
   - Selects the #1 ranked property (Alto Prado, 95 pts).
   - Reads "Tesis de Selección" and "Puntos a verificar en la visita".
   - Clicks `"Exportar Dossier a PDF / Imprimir"`.
   - Clicks WhatsApp link to initiate immediate appointment booking.
3. **Verification Points**:
   - Printable HTML/PDF view opens cleanly formatted without page-break defects.
   - Direct WhatsApp message generated for #1 property.
   - All 12 properties in dossier have complete phone and portal links.

### Scenario 4-4: "The Systematic Catalog Triage Journey"
1. **User Goal**: User conducts thorough review of 50+ listings, systematically triaging options.
2. **Execution Steps**:
   - User iterates through the active listing feed.
   - Marks 10 properties as `"Descartado"` (e.g. no elevator, older building).
   - Verifies "Descartados" count is 10, and active count is `Total - 10`.
   - Toggles `"Ocultar descartados"` switch; discarded cards disappear from main feed.
   - Realizes an error on property #4, navigates to "Descartados" tab, and clicks `"Restaurar"`.
3. **Verification Points**:
   - Property #4 restores to "Por contactar".
   - Active count increments by 1; Descartados decrements by 1.
   - Changes persist cleanly after browser refresh.

---

## 3.6 Test Runner Architecture, Assertions & Pass/Fail Semantics

### Test Runner Architecture
To ensure effortless execution on the user's Windows environment (avoiding PowerShell script execution restriction pitfalls), the E2E testing harness is implemented with **two native execution modes**:

```
                              ┌────────────────────────────────────────┐
                              │           E2E Test Suite               │
                              │  (Tiers 1-4: 36+ Total Assertions)     │
                              └───────────────────┬────────────────────┘
                                                  │
                      ┌───────────────────────────┴───────────────────────────┐
                      ▼                                                       ▼
        [ Mode A: Python Native CLI ]                           [ Mode B: Node Native CLI ]
        Command:                                                Command:
        python tests/run_e2e_suite.py                           node --test tests/e2e/*.test.js
        Dependencies:                                           Dependencies:
        Python 3.12 Standard Library (unittest, json, urllib)   Node 24 Built-in (node:test, node:assert)
        Status: 100% Out-of-the-box Windows Compatible          Status: 100% Zero-npm Compatible
```

### Automated Assertion Standards:
1. **Contract Invariant Assertions**:
   - Strict numeric upper bounds: `assert item['total_price'] <= 2500000`
   - Mathematical identity: `assert item['total_price'] == item['canon_price'] + item['admin_price']`
   - Geographic membership: `assert item['neighborhood'] in NORTH_SECTORS`
2. **DOM / UI Assertions**:
   - Element count matching: `assert len(rendered_cards) == expected_filtered_count`
   - Attribute & text presence: `assert "$ 2." in price_badge.text`
   - WhatsApp URL regex: `assert re.match(r"^https:\/\/wa\.me\/57[0-9]{10}\?text=.+", href)`
3. **Persistence Assertions**:
   - Round-trip serialization equality: `assert json.loads(stored_state) == expected_state`

### Pass/Fail Semantics & Exit Codes:
- **Success (PASS)**:
  - Return Code: `0`
  - Output: Full green terminal report summarizing total tests passed across Tiers 1–4.
  - Generates `test-results.json` with execution timestamp, duration, and test status.
- **Failure (FAIL)**:
  - Return Code: `1`
  - Output: Immediate red failure banner detailing:
    - Failed Test ID (e.g. `[FAIL] Tier 1 - R1-2: Price ceiling violation`)
    - Offending Property ID / Payload
    - Expected vs. Actual values
    - Full call stack trace.

---

# 4. Synthesis, Downstream Dependencies & Implementation Roadmap

### Inter-Agent Alignment:
- **With `explorer_survey_1` (Portals & Extraction Engine — R1)**:
  - The MFVI scoring model depends on `explorer_survey_1` outputting standardized fields (`canon_price`, `admin_price`, `total_price`, `area_m2`, `neighborhood`, `parking`, `contact.phone`, `contact.whatsapp`).
  - Tier 1 and Tier 2 tests serve as the gatekeeper acceptance suite for M1.
- **With `explorer_survey_2` (Dashboard & Local Persistence — R2)**:
  - The interactive dossier view and WhatsApp click-to-chat triggers will integrate directly into the web dashboard layout specified by `explorer_survey_2`.
  - Tier 1 (R2), Tier 3 (Cross-Feature), and Tier 4 (User Journeys) validate the dashboard's filtering engine and `localStorage` persistence.

### Downstream Milestones Roadmap:
1. **Milestone M1 (Data Pipeline)**: Implement multi-portal extraction and validate against Tier 1 (R1) & Tier 2.
2. **Milestone M2 (Dashboard UI)**: Implement local web dashboard and validate against Tier 1 (R2) & Tier 3.
3. **Milestone M3 (Curated Dossier)**: Generate Markdown, Web, and PDF/HTML formats of the curated 10-15 properties and validate against Tier 1 (R3).
4. **Milestone M-E2E (Final Suite Execution)**: Execute the full automated runner across all 4 Tiers, achieving 100% PASS before user delivery.

---
*Report compiled and certified by `explorer_survey_3` — Teamwork Explorer Subagent.*
