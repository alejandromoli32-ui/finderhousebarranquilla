# Milestone 3 (M3) Changes Log — worker_m3_1

**Date**: 2026-09-13  
**Milestone**: M3 — Curated Immediate Visit Dossier & Contact Sheets  
**Status**: Completed & Verified  

---

## 1. `dossier_generator.py` (New File)
- **Multi-Factor Value Index (MFVI)**:
  - 100-point scoring algorithm with 5 genuine dimensions:
    - Dimension 1: Price per m² efficiency (25 pts): Cost/m² calculated as `total_price / area_m2` with 5 tiered score brackets.
    - Dimension 2: Location prestige & security in Barranquilla Norte (25 pts): Tiered by neighborhood (Tier A+ 25 pts, Tier A 22 pts, Tier B+ 18 pts, Tier B 14 pts).
    - Dimension 3: Space & layout (20 pts): Evaluates bedrooms (up to 6 pts), bathrooms (up to 5 pts), parking (up to 5 pts), and area bonus (up to 4 pts).
    - Dimension 4: Stratum & amenities (15 pts): Stratum (up to 6 pts) + natural language token scanning for key amenities (piscina, gimnasio, ascensor, vigilancia 24h, portería, balcón/brisa, planta eléctrica, cocina integral, BBQ, parque infantil) up to 9 pts.
    - Dimension 5: Immediate contact readiness (15 pts): Direct WhatsApp (up to 8 pts), verified phone (4 pts), and identified agency/broker (3 pts).
- **Curated Selection Funnel (`select_curated_properties`)**:
  - Hard binary filter: `total_price <= 2.500.000 COP`, images >= 3, active contact, valid URL.
  - Quality score threshold: MFVI >= 75.0 points.
  - Quota and diversity balancing: Caps any single neighborhood to max 4 to guarantee broad geographic representation across Norte (Riomar, Altos de Riomar, Villa Country, Villa Santos, San Vicente, Miramar, Paraíso, El Tabor).
  - Selects exactly 15 standout properties.
- **Export Engines**:
  - Writes standalone `DOSSIER_VISITAS.md` in Spanish (63.6 KB).
  - Exports structured JSON `data/dossier_curado.json` for frontend consumption.

---

## 2. `DOSSIER_VISITAS.md` (Generated Deliverable)
- **Section 1: Resumen Ejecutivo del Mercado y Métricas Clave**:
  - Evaluated 172 listings; selected 15 finalists.
  - Price range: $1.853.200 to $2.500.000 COP.
  - Average total: $2.210.031 COP (Canon: $1.938.074, Admin: $271.957).
  - Average cost per m²: $23.172 COP/m².
  - Fast-Track Picks: Top Executive (Villa Country `MQ-20802-M7027822`), Top Family (Altos de Riomar `MERGED-9851-M6595771-193354024`), Best Value/m² (El Tabor `MQ-9851-M6921994`).
- **Section 2: Tabla Maestra Comparativa de Selección (Top 15)**:
  - Dense comparative table with Rank, Ref ID, Barrio, Tipo, Área, Hab, Baños, Parq, Canon, Admin, Total Mes, $/m², Score MFVI, and direct WhatsApp booking link.
- **Section 3: Fichas Técnicas Detalladas de Cada Inmueble (15 Factsheets)**:
  - Includes Rank, title, neighborhood, score badge (Selección Diamante / Oro / Plata).
  - Photo preview link for every listing.
  - Financial breakdown (Canon, Admin, Total, $/m²).
  - Physical specifications and distribution.
  - Detected amenities checklist.
  - Curator's Thesis ("Tesis del Curador").
  - On-site visit inspection checklist (hydraulics/pressure, orientation/cooling shadow, power plant backup, parking space).
  - Contact info (phone, agency) and one-click WhatsApp link with prefilled booking message.
- **Section 4: Itinerario y Ruta Logística Sugerida de Visitas**:
  - Grouped into 4 geographical afternoon/morning circuits from Wednesday to Saturday:
    - Día 1 (Miércoles Tarde): Circuito Alto Prado & Villa Country.
    - Día 2 (Jueves Tarde): Circuito Riomar & Altos de Riomar.
    - Día 3 (Viernes Tarde): Circuito Villa Santos & Buenavista.
    - Día 4 (Sábado Mañana): Circuito Miramar, Paraíso & Villa Carolina.
- **Section 5: Protocolo de Arrendamiento y Documentación en Barranquilla**:
  - Guides tenant on insurer standards (Seguros Bolívar, Sura, El Libertador, FianzaCrédito).
  - Documents required for employees, independent contractors, and real-estate co-debtors.

---

## 3. `data/dossier_curado.json` (Exported Dataset)
- JSON container with metadata (`generated_at`, `total_curated`), list of 15 `property_ids`, and structured property records including `whatsapp_url`, `mfvi_score`, `tier`, and `cost_per_m2`.

---

## 4. `web/index.html` (Modified)
- Added `#dossierQuickBtn` in `.header-actions`: 1-click button labeled `🏆 Dossier Curado (Top 15)`.
- Added `#tabDossier` in `.status-tabs`: `🏆 Dossier Curado (Top Visitas) <span class="tab-count" id="countTabDossier">15</span>`.

---

## 5. `web/app.js` (Modified)
- Embedded `DEFAULT_DOSSIER_IDS` array of the 15 curated property IDs to guarantee resilient operation even in offline/fixture mode.
- Added `state.dossierIds = new Set(DEFAULT_DOSSIER_IDS)` and `state.curatedProperties`.
- Extended `initApp()` to attempt fetching `/data/dossier_curado.json` dynamically with graceful fallback.
- Added `statusTab === 'dossier'` handling in `applyFilters()`.
- Added rank preservation when viewing the dossier under default sort.
- In `renderCardHtml()`: Added `🏆 Top Visita` golden badge on property cards that are part of the curated dossier.
- In `updateAllBadgesAndCounters()`: Added update for `el.countTabDossier`.
- In `setupEventListeners()`: Added click handler for `#dossierQuickBtn` to switch active tab to `dossier` and apply filters with toast notification.
- In `resetAllFilters()`: Robust tab reset ensuring `todos` tab is reactivated.

---

## 6. `web/styles.css` (Modified)
- Added styling for `.tab-btn.tab-dossier` and `.tab-btn.tab-dossier.active` with Caribbean solar amber accents.

---

## 7. `tests/test_dossier.py` (New File)
- 8 comprehensive automated unit and integration tests:
  1. `test_dossier_count_bounds`: Confirms 10 <= count <= 15 and no duplicate IDs.
  2. `test_dossier_price_ceiling_strict`: Confirms total_price <= 2.500.000 COP and canon + admin == total for all 15 items.
  3. `test_dossier_geography_north_only`: Confirms all 15 properties belong to Barranquilla Norte sectors.
  4. `test_dossier_contact_and_urls_validity`: Confirms valid HTTP(S) portal links, phone numbers, and WhatsApp deep links.
  5. `test_mfvi_scoring_algorithm_and_weights`: Confirms mathematical accuracy of price/m², location, space, amenities, contact weights, and >= 75 pts score threshold.
  6. `test_dossier_markdown_sections_and_completeness`: Confirms presence of all required sections, tables, factsheets, and 4-day itinerary.
  7. `test_dashboard_integration_and_parity`: Confirms web UI components (`#tabDossier`, `#dossierQuickBtn`, `dossierIds`) and cross-referencing with master database.
  8. `test_whatsapp_prefilled_message_content`: Confirms WhatsApp deep link format and presence of property ID and visit inquiry in encoded message.
