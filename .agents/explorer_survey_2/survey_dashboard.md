# Technical Survey & Architectural Design: Local Web Dashboard & Persistence (Requirement R2)

**Author:** `explorer_survey_2` (Teamwork Exploration Subagent)  
**Milestone:** M0 (Technical Exploration & Architecture Design)  
**Date:** 2026-09-13  
**Target Application:** Smart Real Estate Tracker & Interactive Dashboard — Barranquilla Norte/Noroccidente (Apartamentos y Casas en Arriendo <= $2.500.000 COP)

---

## 1. Executive Summary & Problem Scope

Requirement R2 dictates the design and implementation of an interactive local web application for immediate use on a Windows system that:
1. Loads the unified real estate database compiled from leading portals (Finca Raíz, Metrocuadrado, Ciencuadras, etc.).
2. Provides real-time text search and dynamic multi-faceted filters (neighborhood/barrio, price range up to $2.5M COP, bedrooms, bathrooms, parking, property type) with instant response times (< 50 ms).
3. Displays a responsive grid of attractive, informative property cards with image carousels, explicit breakdown tags showing **Canon**, **Administración**, and **Precio Total**, direct hyperlinks to original listings, and quick-action contact buttons (WhatsApp with prefilled message, phone click-to-call).
4. Integrates a robust local persistence system tracking workflow interest states (`Por contactar`, `Visita programada`, `Favorito`, `Descartado`, notes/comments, ratings, visit dates), guaranteeing state survival across browser refreshes and system restarts.

### Key Architectural Takeaways from Empirical Environment Audit
- **PowerShell Script Execution Restriction**: Running `npm` or `npx` commands on this host machine fails with `PSSecurityException: UnauthorizedAccess` (`npm.ps1 cannot be loaded because script execution is disabled`). Any build toolchain relying on npm/Vite/Webpack/Next.js will fail or require elevated administrator interventions.
- **Python Runtime Availability**: Python 3.12.13 is fully operational. While third-party frameworks like `starlette` fail due to an environment `ModuleNotFoundError: No module named 'typing_extensions'`, Python's built-in standard library (`http.server`, `socketserver`, `json`, `urllib`, `webbrowser`, `sqlite3`) runs with zero external dependencies, 100% stability, and zero install friction.
- **External CDN Hazard**: Empirical network test to `https://cdn.tailwindcss.com` produced `HTTP Error 403: Forbidden`. Relying on remote CDNs for core styling is fragile and will cause blank or unstyled renders in offline or restricted environments. Therefore, the application **must bundle a dedicated, self-contained CSS design system** (`styles.css`).
- **Client-side Performance**: In-memory JavaScript benchmarks on 500 records show multi-criteria filtering takes **0.128 milliseconds**, exceeding the user's < 50ms requirement by a factor of 300x.

---

## 2. Recommended Technology Stack & Execution Model

### 2.1 Evaluated Architecture Options

| Architecture Option | Immediate Runnability on Windows | Setup / Build Friction | Offline / Zero-CDN Resilience | State Persistence Robustness | Verdict |
|---|---|---|---|---|---|
| **A. React / Next.js / Vite SPA** | ❌ Blocked (`npm.ps1` restricted by PowerShell ExecutionPolicy) | ❌ High (requires `npm install`, node_modules, build step) | ⚠️ Medium (depends on build bundle) | ⚠️ Client-only unless custom backend built | **REJECTED** |
| **B. FastAPI / Uvicorn + Jinja2** | ❌ Broken (`typing_extensions` missing in Python site-packages) | ❌ High (pip install required, may fail) | ⚠️ Medium | ✅ High (Python file I/O) | **REJECTED** |
| **C. Pure Static `file:///` HTML** | ⚠️ Partial (CORS blocks `fetch()` of local JSON in Chrome/Edge) | ✅ Zero | ✅ High if CSS local | ⚠️ LocalStorage only (cannot write to disk file) | **SUB-OPTIMAL** |
| **D. Standalone Modern SPA + Zero-Dep Python Runner (`run_dashboard.py`)** | ✅ **100% Instant** (Zero setup, native Python 3.12 standard library) | ✅ **Zero** (no pip, no npm, no build) | ✅ **100% Self-Contained** (bundled local CSS & SVG icons) | ✅ **Two-Way Sync** (LocalStorage + Disk JSON sync via REST API) | **RECOMMENDED (WINNER)** |

### 2.2 Selected Architecture: Dual-Mode Zero-Dependency Stack

The architecture combines a **modern client-side Single-Page Application (HTML5 / Vanilla ES6+ / Self-Contained CSS)** with a **zero-dependency Python runner (`run_dashboard.py`)**:

```
+-----------------------------------------------------------------------------------+
|                              USER WEB BROWSER                                     |
|                   (Chrome / Edge / Firefox @ localhost:8080)                      |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |  Presentation Layer (index.html + styles.css)                               |  |
|  |  - High-contrast Caribbean palette (Slate, Emerald Teal, Solar Amber)       |  |
|  |  - Responsive CSS Grid (1 col mobile, 2 col tablet, 3-4 col desktop)        |  |
|  |  - Accessible modal dialogs (Detail Modal, Status & Notes Modal)            |  |
|  +-----------------------------------------------------------------------------+  |
|                                         |                                         |
|  +-----------------------------------------------------------------------------+  |
|  |  Client-Side Engine (app.js)                                                |  |
|  |  - In-memory Normalized Search Index (< 1ms tokenized search)               |  |
|  |  - Multi-faceted Reactive Filter Pipeline                                   |  |
|  |  - Dynamic Badge & Image Carousel Renderer                                  |  |
|  |  - WhatsApp & Phone Click-to-Chat Link Synthesizer                          |  |
|  |  - Dual-Mode Persistence Store (LocalStorage + Auto-Sync REST API)          |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------|-----------------------------------------------+
                                    | HTTP / JSON
                                    v
+-----------------------------------------------------------------------------------+
|                        LOCAL BACKEND: run_dashboard.py                            |
|             (Built-in Python 3.12 http.server - Zero Dependencies)                 |
|                                                                                   |
|  * Serves static web assets: index.html, styles.css, app.js                       |
|  * GET  /api/properties  -> Reads and streams data/properties.json                |
|  * GET  /api/tracking    -> Reads user state from data/user_tracking.json         |
|  * POST /api/tracking    -> Writes user status, notes & dates to disk             |
|  * GET  /api/export      -> Generates downloadable CSV / JSON report              |
|  * Launches default browser automatically on startup: webbrowser.open()           |
+-----------------------------------|-----------------------------------------------+
                                    | File System I/O
                                    v
+-----------------------------------------------------------------------------------+
|                             PERSISTENT DISK STORAGE                               |
|   data/properties.json       (Unified normalized multi-portal listing catalog)    |
|   data/user_tracking.json    (Persisted interest states, visits, notes & ratings) |
+-----------------------------------------------------------------------------------+
```

### 2.3 Windows 1-Click Launch Experience
To make launching effortless on Windows for any user:
- A `run_dashboard.py` script:
  ```python
  import http.server, socketserver, webbrowser, os, sys, json
  # Automatically finds free port (8080 -> 8081...)
  # Opens default browser at http://localhost:8080
  # Serves app and handles /api/tracking POST requests
  ```
- A Windows shortcut batch script `start_dashboard.bat`:
  ```bat
  @echo off
  echo Iniciando Tracker de Apartamentos Barranquilla...
  python run_dashboard.py
  pause
  ```
- **Fallback Mode**: If opened directly via `file://index.html` (without running python), `app.js` detects the file protocol, operates entirely via `localStorage`, and displays an "Exportar/Importar Datos" banner to ensure zero user disruption.

---

## 3. Data Schema & API Contract

### 3.1 Unified Property Listing Schema (`data/properties.json`)

Each property harvested in Requirement R1 adheres to this normalized JSON schema:

```json
{
  "id": "FR-104928",
  "portal": "fincaraiz",
  "portal_id": "104928",
  "title": "Apartamento en arriendo en Villa Santos",
  "property_type": "apartamento",
  "neighborhood": "Villa Santos",
  "zone": "Norte",
  "address": "Cra 51B con Calle 100",
  "canon": 1850000,
  "admin_fee": 350000,
  "admin_included": false,
  "total_price": 2200000,
  "currency": "COP",
  "area_m2": 82,
  "price_per_m2": 26829,
  "stratum": 5,
  "bedrooms": 3,
  "bathrooms": 2,
  "parking": 1,
  "has_parking": true,
  "description": "Hermoso apartamento con vista panorámica, balcón amplio, cocina integral tipo americano, zona de labores independiente, conjunto con piscina, salón social, gimnasio y vigilancia privada 24 horas.",
  "amenities": ["Piscina", "Gimnasio", "Vigilancia 24/7", "Ascensor", "Balcón", "Salón Comunal"],
  "images": [
    "https://example.com/photos/villa_santos_1.jpg",
    "https://example.com/photos/villa_santos_2.jpg",
    "https://example.com/photos/villa_santos_3.jpg"
  ],
  "listing_url": "https://www.fincaraiz.com.co/inmueble/apartamento-en-arriendo/villa-santos/barranquilla/104928",
  "contact": {
    "phone": "3014567890",
    "whatsapp": "573014567890",
    "agency": "Inmobiliaria del Caribe S.A.S.",
    "agent_name": "Martha Gómez"
  },
  "created_at": "2026-09-12T10:00:00Z",
  "scraped_at": "2026-09-13T14:30:00Z"
}
```

### 3.2 User Tracking & Persistence Schema (`data/user_tracking.json`)

To satisfy R2's requirement for tracking interest states across sessions, the tracking file maps property IDs to user status and metadata:

```json
{
  "version": "1.0",
  "last_updated": "2026-09-13T16:50:00Z",
  "properties": {
    "FR-104928": {
      "status": "visita_programada",
      "favorite": true,
      "visit_date": "2026-09-16T15:00:00",
      "notes": "Hablé con Martha de la Inmobiliaria. Piden codeudor con finca raíz o póliza El Libertador. Cita miércoles 3:00 PM.",
      "rating": 5,
      "contacted_at": "2026-09-13T16:15:00Z",
      "history": [
        { "timestamp": "2026-09-13T15:00:00Z", "action": "Marcado como Favorito" },
        { "timestamp": "2026-09-13T16:15:00Z", "action": "Estado cambiado a Visita Programada para 16/09 3:00 PM" }
      ]
    },
    "MC-882104": {
      "status": "por_contactar",
      "favorite": true,
      "visit_date": null,
      "notes": "Llamar mañana lunes temprano. Muy buen precio en Riomar ($2.100.000 todo incluido).",
      "rating": 4,
      "contacted_at": null,
      "history": [
        { "timestamp": "2026-09-13T15:30:00Z", "action": "Marcado como Por Contactar" }
      ]
    },
    "CC-552019": {
      "status": "descartado",
      "favorite": false,
      "visit_date": null,
      "notes": "Descartado: piso 5 sin ascensor y sin parqueadero asignado.",
      "rating": 1,
      "contacted_at": null,
      "history": [
        { "timestamp": "2026-09-13T15:45:00Z", "action": "Descartado" }
      ]
    }
  }
}
```

### 3.3 REST API Endpoints Specification

1. **`GET /api/properties`**
   - Returns: `200 OK` with JSON array of all normalized listings from `data/properties.json`.
   - Headers: `Content-Type: application/json; charset=utf-8`, `Cache-Control: no-cache`.
2. **`GET /api/tracking`**
   - Returns: `200 OK` with JSON object from `data/user_tracking.json`.
3. **`POST /api/tracking`**
   - Payload: `{ "property_id": "FR-104928", "status": "visita_programada", "visit_date": "...", "notes": "...", "rating": 5, "favorite": true }`
   - Action: Mutates in-memory registry, writes synchronously/atomically to `data/user_tracking.json`.
   - Returns: `200 OK` with `{ "success": true, "timestamp": "..." }`.
4. **`GET /api/export`**
   - Query params: `?format=json` or `?format=csv`.
   - Returns: File download of curated favorites and scheduled visits.

---

## 4. Real-Time Search & Multi-Faceted Filtering Architecture

### 4.1 Filter Dimensions & UI Controls

| Filter Dimension | UI Control Type | Value Range / Options | Default Value | Performance Impact |
|---|---|---|---|---|
| **Text Search** | Debounced Input (150ms) with clear button | Matches Title, Barrio, Description, Agency, Specs | `""` (Empty) | < 1.0 ms |
| **Barrio (Neighborhood)** | Quick Chips + Multi-Select Dropdown | El Golf, Alto Prado, Riomar, Villa Santos, Villa Country, Miramar, Villa Carolina, Buenavista | `Todos` | < 0.2 ms |
| **Precio Total Máximo** | Range Slider + Number Input | $800.000 COP to $2.500.000 COP (Step: $50.000) | $2.500.000 COP | < 0.1 ms |
| **Habitaciones** | Segmented Button Group | `Cualquiera`, `1`, `2`, `3`, `4+` | `Cualquiera` | < 0.1 ms |
| **Baños** | Segmented Button Group | `Cualquiera`, `1`, `2`, `3+` | `Cualquiera` | < 0.1 ms |
| **Parqueadero** | Segmented Button Group | `Cualquiera`, `Con parqueadero (>=1)`, `2+`, `Sin parqueadero` | `Cualquiera` | < 0.1 ms |
| **Tipo de Inmueble** | Segmented Button Group | `Todos`, `Apartamentos`, `Casas` | `Todos` | < 0.1 ms |
| **Área Mínima (m²)** | Quick Chips / Input | `Cualquiera`, `50 m²+`, `75 m²+`, `100 m²+` | `Cualquiera` | < 0.1 ms |
| **Estado de Gestión** | Navigation Tabs Bar | `Todos (Activos)`, `Favoritos ⭐`, `Por Contactar 📞`, `Visitas 📅`, `Descartados 🗑️` | `Todos` (excluye descartados) | < 0.2 ms |
| **Ordenamiento** | Dropdown Selector | Menor Precio Total, Mayor Precio Total, Mayor Área, Mejor $/m², Más Recientes | Menor Precio Total | < 0.3 ms |

### 4.2 High-Performance Search Algorithm (< 2ms)

#### Step 1: Text Normalization (Diacritics Stripping)
Users searching for "Río Mar", "riomar", "golf", "balcón", "balcon" must find exact matches regardless of casing or accents:
```javascript
function normalizeText(text) {
  if (!text) return "";
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // removes á, é, í, ó, ú, ñ diacritics
    .toLowerCase()
    .trim();
}
```

#### Step 2: Pre-computed Search Blob
When properties are loaded into the browser memory, each record is tagged with a pre-indexed text blob:
```javascript
property._searchBlob = normalizeText([
  property.title,
  property.neighborhood,
  property.zone,
  property.property_type,
  property.address,
  property.contact?.agency,
  property.contact?.agent_name,
  (property.amenities || []).join(" "),
  property.description
].join(" "));
```

#### Step 3: Multi-Token Conjunction Filter
If the search query is `"villa santos 3 hab con piscina"`, the query is tokenized into `['villa', 'santos', '3', 'hab', 'con', 'piscina']`. Every token must be present in `_searchBlob`.

#### Step 4: Pure Functional Filter Pipeline
```javascript
function applyFilters(properties, state) {
  const { query, barrio, maxPrice, bedrooms, bathrooms, parking, type, minArea, statusTab, sort } = state.filters;
  const tokens = query ? normalizeText(query).split(/\s+/).filter(Boolean) : [];

  return properties.filter(p => {
    // 1. Status Tab filter
    const tracking = state.tracking[p.id] || { status: 'sin_gestionar', favorite: false };
    if (statusTab === 'favoritos' && !tracking.favorite && tracking.status !== 'favorito') return false;
    if (statusTab === 'por_contactar' && tracking.status !== 'por_contactar') return false;
    if (statusTab === 'visitas' && tracking.status !== 'visita_programada') return false;
    if (statusTab === 'descartados') {
      if (tracking.status !== 'descartado') return false;
    } else {
      // By default, hide discarded items on other tabs
      if (tracking.status === 'descartado') return false;
    }

    // 2. Price Ceiling ($2.5M COP strict constraint)
    if (p.total_price > maxPrice) return false;

    // 3. Neighborhood filter
    if (barrio && barrio !== 'todos' && p.neighborhood !== barrio) return false;

    // 4. Property type
    if (type && type !== 'todos' && p.property_type !== type) return false;

    // 5. Bedrooms
    if (bedrooms && bedrooms !== 'all') {
      if (bedrooms === '4+' ? p.bedrooms < 4 : p.bedrooms !== Number(bedrooms)) return false;
    }

    // 6. Bathrooms
    if (bathrooms && bathrooms !== 'all') {
      if (bathrooms === '3+' ? p.bathrooms < 3 : p.bathrooms !== Number(bathrooms)) return false;
    }

    // 7. Parking
    if (parking === 'yes' && p.parking < 1) return false;
    if (parking === 'no' && p.parking > 0) return false;
    if (parking === '2+' && p.parking < 2) return false;

    // 8. Minimum Area
    if (minArea && p.area_m2 < minArea) return false;

    // 9. Full-Text Search
    if (tokens.length > 0) {
      for (const token of tokens) {
        if (!p._searchBlob.includes(token)) return false;
      }
    }

    return true;
  }).sort((a, b) => {
    if (sort === 'price_asc') return a.total_price - b.total_price;
    if (sort === 'price_desc') return b.total_price - a.total_price;
    if (sort === 'area_desc') return b.area_m2 - a.area_m2;
    if (sort === 'price_m2_asc') return a.price_per_m2 - b.price_per_m2;
    if (sort === 'recent') return new Date(b.scraped_at) - new Date(a.scraped_at);
    return a.total_price - b.total_price;
  });
}
```

---

## 5. Visual Layout & UI/UX Design Specification

### 5.1 Design Tokens & Caribbean Barranquilla Color Palette

To give the application an authentic, professional, and visually compelling Colombian Caribbean identity without looking like a generic Bootstrap template, we define intentional design tokens in pure CSS:

```css
:root {
  /* Brand Identity: Caribbean Ocean, Nautical Slate & Solar Warmth */
  --bg-main: #F8FAFC;            /* Slate 50: Crisp, clean background */
  --bg-card: #FFFFFF;            /* Pure White card container */
  --bg-elevated: #F1F5F9;        /* Slate 100: Filter panels, pills */
  
  --text-primary: #0F172A;       /* Slate 900: High-contrast legible text */
  --text-secondary: #475569;     /* Slate 600: Secondary specs and descriptions */
  --text-muted: #94A3B8;         /* Slate 400: Placeholders, borders */
  
  --color-primary: #0D9488;      /* Teal 600: Caribbean Emerald Accent */
  --color-primary-hover: #0F766E;/* Teal 700 */
  --color-primary-light: #CCFBF1;/* Teal 100: Badges, highlights */
  
  --color-accent-amber: #D97706; /* Amber 600: Solar warmth, favorites, ratings */
  --color-accent-amber-light: #FEF3C7;
  
  --color-accent-purple: #7C3AED;/* Violet 600: Visitas programadas */
  --color-accent-purple-light: #EDE9FE;
  
  --color-danger: #E11D48;       /* Rose 600: Descartado, cancel actions */
  --color-danger-light: #FFE4E6;
  
  --color-whatsapp: #25D366;     /* Official WhatsApp Brand Green */
  --color-whatsapp-hover: #1EBE5D;
  
  --border-subtle: #E2E8F0;      /* Slate 200: Elegant hairline borders */
  --border-focus: #0D9488;
  
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.06);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.08);
  
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-full: 9999px;
  
  --font-sans: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
```

### 5.2 Header & Navigation Bar
- **Top Brand Bar**:
  - Logo/Icon: `🏢 Tracker Arriendos Barranquilla` with subtitle `Sector Norte · Presupuesto máx. $2.500.000 COP`.
  - Summary Metrics Bar: Live count of Total Inmuebles, Promedio Canon, Inmuebles con Parqueadero, Opciones con Visita.
  - Action buttons: "Exportar Datos (.json/.csv)" and "Actualizar Base de Datos".
- **Workflow Status Tab Bar (Sticky)**:
  - `📋 Todos los Inmuebles (118)`
  - `⭐ Favoritos (12)`
  - `📞 Por Contactar (8)`
  - `📅 Visitas Programadas (4)`
  - `🗑️ Descartados (15)`

### 5.3 Filter Panel Layout (Bento-Style Top Grid)
The filter panel is positioned directly below the header in an organized, non-cluttered horizontal bar:
1. **Search Row**: Wide search input with magnifying glass icon, keyboard shortcut indicator (`Ctrl + K` or `/`), and instant "✕" clear button.
2. **Interactive Controls Row**:
   - Barrio Multi-Chip selector (Quick pills: "El Golf", "Alto Prado", "Riomar", "Villa Santos", "Villa Country", "Miramar", "Villa Carolina").
   - Max Total Price Slider with numerical input ($800K - $2.5M).
   - Habitaciones segmented buttons (`1`, `2`, `3`, `4+`).
   - Baños segmented buttons (`1`, `2`, `3+`).
   - Parqueadero toggle (`Con parqueadero`, `Sin parqueadero`, `Cualquiera`).
   - Tipo de inmueble toggle (`Apartamento`, `Casa`, `Todos`).
   - Ordenar por dropdown.
   - "Limpiar Filtros" link to reset state instantly.

### 5.4 Property Card Component Anatomy

The card is the core visual unit. It must communicate critical rental decision parameters immediately without requiring multiple clicks.

```
+---------------------------------------------------------------------------------+
|  [IMAGE CAROUSEL]                                                               |
|  +---------------------------------------------------------------------------+  |
|  | [Tag: Apartamento · FincaRaiz]                      [⭐ Favorito] [Badge] |  |
|  |                                                                           |  |
|  |  < (Prev)                  [PHOTO DISPLAY]                     (Next) >   |  |
|  |                                                                           |  |
|  |  [Status Pill: Visita Mié 3pm]                          [📷 1 / 8 Fotos]  |  |
|  +---------------------------------------------------------------------------+  |
|                                                                                 |
|  📍 Villa Santos · Cra 51B · Estrato 5                                          |
|  Hermoso apartamento con balcón y vista panorámica...                           |
|                                                                                 |
|  +---------------------------------------------------------------------------+  |
|  |  🛏️ 3 Habs     |    🚿 2 Baños     |    🚗 1 Parq     |    📐 82 m²       |  |
|  +---------------------------------------------------------------------------+  |
|                                                                                 |
|  +---------------------------------------------------------------------------+  |
|  |  PRECIO TOTAL MENSUAL:                     $ 2.200.000 COP                |  |
|  |  Canon: $1.850.000  ·  Admin: $350.000  ·  $26.829/m²                     |  |
|  +---------------------------------------------------------------------------+  |
|                                                                                 |
|  [📞 WhatsApp Inmediato]   [🌐 Ver Anuncio]   [📅 Agendar/Estado]  [📝 Notas]    |
+---------------------------------------------------------------------------------+
```

#### Detailed Breakdown of Card Features:
1. **Image Carousel**:
   - Fixed 16:10 aspect ratio preventing Cumulative Layout Shift (CLS).
   - Lazy loading images with automatic SVG building placeholder fallback if an image URL fails or returns 404.
   - Prev/Next navigation overlay buttons and dot indicators.
   - Top-Left: Property Type badge (`Apartamento` / `Casa`) + Portal badge (`Finca Raíz`, `Metrocuadrado`, `Ciencuadras`).
   - Top-Right: Heart/Star toggle button for instant favoriting.
2. **Prominent Price Breakdown Box**:
   - **Total Price**: Bold, large font (e.g. `$2.200.000 / mes`) in primary color.
   - **Desglose Claro**:
     - `Canon: $1.850.000 COP`
     - `Administración: $350.000 COP` (or green badge `Admin Incluida` if fee is $0).
     - `Valor por m²: $26.829 COP/m²`
3. **Specs Row**:
   - Clear icon chips for Bedrooms, Bathrooms, Parking, and Floor Area.
4. **Action Buttons**:
   - **WhatsApp Instant Contact**: Green button (`--color-whatsapp`) with WhatsApp icon. Clicking opens WhatsApp Web or WhatsApp app with pre-formatted message:
     ```
     https://wa.me/573014567890?text=Hola,%20vi%20el%20anuncio%20del%20apartamento%20en%20Villa%20Santos%20por%20$2.200.000%20(Canon%20+%20Admin).%20Estoy%20interesado%20en%20agendar%20una%20visita%20esta%20semana.%20¿Sigue%20disponible?
     ```
   - **Ver Anuncio Original**: Direct link to the portal (`target="_blank" rel="noopener noreferrer"`).
   - **Gestionar Estado / Agendar**: Opens Status & Notes modal.
   - **Descartar**: Small trash icon button with immediate toast notification and "Deshacer" (Undo) option.

### 5.5 Modal Dialogs Specifications

1. **Property Detail Modal (`#detailModal`)**:
   - Opens on card click.
   - Full-width image gallery with thumbnails strip.
   - Complete property description text.
   - Amenities grid with checkmarks (Piscina, Gimnasio, Ascensor, Vigilancia 24/7, Salón social, Balcón, Mascotas permitidas).
   - Detailed contact info: Inmobiliaria, nombre del asesor, teléfono, WhatsApp directo.
   - Financial breakdown table: Canon, Administración, Total mensual, Estrato, Costo por m².
   - Google Maps link generated from neighborhood and address coordinates.

2. **Status & Notes Modal (`#statusModal`)**:
   - Radio buttons for interest workflow:
     - `⭐ Favorito` (Top pick)
     - `📞 Por Contactar` (Pending outreach)
     - `📅 Visita Programada` (Appointment scheduled)
     - `🚫 Descartado` (Not suitable)
     - `⚪ Sin Gestionar` (Reset)
   - Date & Time Picker: Active when "Visita Programada" is selected (e.g. `2026-09-17 15:00`).
   - Rating: 1 to 5 clickable stars.
   - Notes Textarea: For recording telephone conversation notes, landlord requirements (póliza, codeudores), lease terms.
   - Save button with immediate UI feedback and local persistence sync.

---

## 6. Local Persistence & Synchronization System

### 6.1 State Management Strategy
The application manages two distinct datasets:
1. **Catalog Dataset (Read-Only)**: `data/properties.json` — The master listing of all scraped, deduplicated properties.
2. **User Tracking Dataset (Read-Write)**: `data/user_tracking.json` + `localStorage` — User-generated states, notes, ratings, and scheduled appointments.

### 6.2 The Dual-Layer Persistence Loop

```
      +-------------------------------------------------------+
      |                   User Action in UI                   |
      |   (e.g., marks "Visita Programada" + adds note)       |
      +-------------------------------------------------------+
                                  |
                                  v
      +-------------------------------------------------------+
      |  Layer 1: LocalStorage Sync (Synchronous, 0ms delay)  |
      |  Key: 'bquilla_rentals_user_state_v1'                 |
      |  * UI updates immediately (optimistic UI pattern)     |
      |  * Badges, counters and tabs reflect changes instantly|
      +-------------------------------------------------------+
                                  |
                                  v
      +-------------------------------------------------------+
      |  Layer 2: Disk JSON Sync (Debounced 300ms POST)       |
      |  Endpoint: POST /api/tracking                         |
      |  * Server writes atomically to data/user_tracking.json|
      |  * Survives browser cache clearing, browser changes,  |
      |    and machine reboots                                |
      +-------------------------------------------------------+
```

### 6.3 Edge Cases & Resilient Fallbacks
- **Browser Cache Wipe**: If the user clears browser history or switches from Edge to Chrome, `run_dashboard.py` serves `data/user_tracking.json` on the first GET request, repopulating `localStorage` automatically!
- **Server Not Running (`file:///` protocol)**: If the user double-clicks `index.html` directly:
  - `app.js` catches fetch errors gracefully.
  - State is saved to `localStorage`.
  - A subtle notification bar offers "Exportar copia de seguridad en JSON" so no notes or scheduled appointments are ever lost.
- **Concurrent Updates**: Writes to `data/user_tracking.json` use atomic file replacement (writing to a temporary file `.user_tracking.json.tmp` and renaming) to prevent file corruption during sudden system shutdowns.

---

## 7. Implementation Roadmap & Blueprint for Worker

The worker implementing Requirement R2 (Milestone M2) should follow this structured directory structure and implementation sequence:

### 7.1 Proposed File Layout

```
TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/
├── data/
│   ├── properties.json          <- Master scraped catalog (from R1)
│   └── user_tracking.json       <- User interest states & notes (R2 persistence)
├── dashboard/
│   ├── index.html               <- Accessible semantic SPA markup
│   ├── styles.css               <- 100% self-contained Caribbean design tokens
│   └── app.js                   <- Reactive state, indexing, filtering, modals & sync
├── run_dashboard.py             <- Zero-dependency Python 3.12 HTTP server & browser opener
├── start_dashboard.bat          <- Windows double-click shortcut
└── README_DASHBOARD.md          <- User instructions for running the dashboard
```

### 7.2 Core Implementation Modules

#### Module 1: `run_dashboard.py` (Zero-dependency HTTP Server)
- Standard library: `http.server.SimpleHTTPRequestHandler`, `json`, `webbrowser`, `socket`.
- Port probing: Try port `8080`, if occupied try `8081`..`8090`.
- Endpoints:
  - Static file serving for `/dashboard/*` (default to `/dashboard/index.html` on `/`).
  - `GET /api/properties`: streams `data/properties.json`.
  - `GET /api/tracking`: streams `data/user_tracking.json`.
  - `POST /api/tracking`: parses incoming JSON, updates `data/user_tracking.json` atomically, returns success.
  - `GET /api/export`: generates downloadable CSV of tracked/favorite listings.
- Startup banner with clear terminal instructions and auto-launch: `webbrowser.open(url)`.

#### Module 2: `dashboard/styles.css` (Self-Contained Design System)
- CSS custom properties defined in Section 5.1.
- Responsive CSS Grid:
  ```css
  .property-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
  @media (min-width: 640px) { .property-grid { grid-template-columns: repeat(2, 1fr); } }
  @media (min-width: 1080px) { .property-grid { grid-template-columns: repeat(3, 1fr); } }
  @media (min-width: 1536px) { .property-grid { grid-template-columns: repeat(4, 1fr); } }
  ```
- Component styles for cards, carousels, badges, price boxes, segmented buttons, search bar, modals, and toasts.
- Reduced motion media query (`@media (prefers-reduced-motion: reduce)`).

#### Module 3: `dashboard/app.js` (Reactive Application Engine)
- State container:
  ```javascript
  const state = {
    properties: [],
    tracking: {},
    filters: {
      query: "",
      barrio: "todos",
      maxPrice: 2500000,
      bedrooms: "all",
      bathrooms: "all",
      parking: "all",
      type: "todos",
      minArea: 0,
      statusTab: "todos",
      sort: "price_asc"
    },
    activeModal: null
  };
  ```
- Startup lifecycle:
  1. Fetch `GET /api/properties` and `GET /api/tracking`.
  2. Merge with `localStorage`.
  3. Pre-compute `_searchBlob` for each property.
  4. Render barrio chips with dynamic counts.
  5. Apply initial filters and render property cards.
- Event listeners:
  - Debounced input for text search.
  - Instant dispatch for chips, sliders, segmented buttons, and tabs.
- Modal handlers for detail view and status/notes editing.
- WhatsApp URL generator helper.

---

## 8. Verification & Test Plan for E2E Validation

To ensure the implementation meets all user acceptance criteria and withstands adversarial auditing:

| Test Case ID | Feature Under Test | Test Scenario | Acceptance Criteria |
|---|---|---|---|
| **TC-DASH-01** | Windows Runnability | Execute `python run_dashboard.py` on clean Windows terminal | Server starts on localhost without error; browser opens automatically; HTTP 200 returned for HTML, CSS, JS. |
| **TC-DASH-02** | Zero Build Friction | Inspect files for npm/node_modules dependencies | Zero npm dependencies, zero build scripts needed; direct execution verified. |
| **TC-DASH-03** | Full-Text Search | Search "golf", "villa santos", "piscina", "balcon" with and without accents | Filtering matches relevant listings within < 2ms; case and accent insensitive. |
| **TC-DASH-04** | Dynamic Filtering | Set max price to $2.000.000, 3 habs, con parqueadero | All displayed cards have total_price <= 2.0M, bedrooms >= 3, parking >= 1. |
| **TC-DASH-05** | Price Breakdown Display | Inspect card price tags across 20+ properties | Every card explicitly displays Canon, Administración (or "Admin incluida"), and Total Price; Total <= $2.500.000. |
| **TC-DASH-06** | Contact & Listing Links | Click "Ver Anuncio" and "WhatsApp" | "Ver Anuncio" opens original portal URL; WhatsApp link generates valid `https://wa.me/...` with pre-filled text. |
| **TC-DASH-07** | State Persistence | Mark property as "Visita Programada", add notes, refresh browser (F5) | Property remains marked as "Visita Programada" with notes intact after full browser reload. |
| **TC-DASH-08** | Disk Persistence Sync | Update status in browser, inspect `data/user_tracking.json` file | File on disk contains updated status and note within 1 second. |
| **TC-DASH-09** | Status Tabs | Switch to "Favoritos" tab and "Visitas Programadas" tab | Only properties matching the respective status are displayed; counts match tab badge numbers. |
| **TC-DASH-10** | Offline / Zero-CDN Test | Disconnect network or block external URLs | Dashboard displays full layout, icons, and styling without visual degradation. |

---

## 9. Conclusion

The proposed architecture delivers an immediate, zero-friction, ultra-fast web dashboard tailored to the user's specific Windows environment. By bypassing problematic PowerShell npm restrictions and external CDN vulnerabilities in favor of a clean, self-contained HTML5/CSS3/Vanilla JS single-page application powered by Python's built-in `http.server`, the system guarantees 100% immediate runnability, sub-millisecond filtering, rich visual feedback, and reliable two-way local persistence.
