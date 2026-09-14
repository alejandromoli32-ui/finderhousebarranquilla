# Forensic Audit Report: Milestone 2 (M2) — Local Web Dashboard & State Persistence

**Auditor:** `auditor_m2_1` (Forensic Integrity Auditor, Critic, Specialist)  
**Recipient:** `orchestrator_1` (Conversation ID: `78e1bffd-c00b-4edf-9b66-26fc5574a726`)  
**Work Product:** Milestone 2 (`run_dashboard.py`, `web/index.html`, `web/styles.css`, `web/app.js`, `tests/test_dashboard.py`, `start_dashboard.bat`, `data/user_tracking.json`)  
**Profile:** General Project (Development Mode per `ORIGINAL_REQUEST.md`)  
**Date:** 2026-09-13  
**Verdict:** **`CLEAN`** *(Integrity & Authenticity)* | **`DEFECTS FLAGGED`** *(Windows CLI Runtime Crash & Adversarial Robustness)*  

---

## Forensic Integrity Summary

| Forensic Check | Status | Empirical Finding |
|---|---|---|
| **1. Hardcoded Test Results** | **PASS** | No dummy strings, hardcoded responses, or mocked outputs in `run_dashboard.py` or `web/app.js`. All 172 real properties are loaded and served dynamically. |
| **2. Facade Implementations** | **PASS** | Full, authentic logic implemented: in-memory diacritic search (`normalize('NFD')`), multi-faceted filtering, carousel navigation, modals, WhatsApp link formatting, dual-layer storage sync. |
| **3. Fabricated Verification Outputs** | **PASS** | No pre-populated test logs or fake attestations. Automated test suite executes live requests against real HTTP sockets. |
| **4. Self-Certifying Tests** | **PASS** | `tests/test_dashboard.py` uses independent HTTP clients (`urllib.request`) against dynamically bound ports, verifying schema, status codes, concurrency, and filesystem atomic writes. |
| **5. Execution Delegation** | **PASS** | 100% Python 3.12 standard library, zero external npm or CDN dependencies (offline Caribbean Nautical styling, pure vanilla JS). |
| **6. Persistence Across Sessions** | **PASS** | Empirically verified: POSTed tracking records survive process kill and reload cleanly in a brand-new server process from `data/user_tracking.json`. |

---

## 1. Observation

### 1.1 Static Analysis Observations

1. **`run_dashboard.py` (420 lines)**:
   - Zero third-party dependencies (`http.server.ThreadingHTTPServer`, `socketserver`, `json`, `os`, `pathlib`, `threading`, `urllib.parse`, `mimetypes`, `webbrowser`, `argparse`).
   - Line 30: Thread synchronization using `_TRACKING_LOCK = threading.RLock()`.
   - Lines 71-80: Atomic persistence via temporary file `TRACKING_FILE.with_suffix(".json.tmp")` and `os.replace`.
   - Lines 159-242: Real REST routes (`/api/properties`, `/data/inmuebles_barranquilla.json`, `/data/inmuebles_barranquilla.csv`, `/api/tracking`, `/api/export`).
   - Lines 244-275: Static file routing with strict path traversal prevention (`resolved_target.is_relative_to(WEB_DIR) or resolved_target.is_relative_to(BASE_DIR)`).

2. **`web/index.html` (431 lines)**:
   - Self-contained semantic HTML5. No external CDN `<script>` or `<link>` tags.
   - Genuine UI structure: Branding, live Stats Bar, Search bar with Ctrl+K shortcut, 41-barrio dropdown, 10 quick pills, price range slider ($1.0M - $2.5M), segmented buttons (Habitaciones, Baños, Parqueadero, Tipo), Status workflow tabs (Todos, Favoritos, Visitas, Por contactar, Descartados), Property Card Grid, Empty state container, Property Detail Modal with carousel and financial breakdown box, Status & Notes Tracking Modal with 5-star rating and date picker, Toast notifications container.

3. **`web/styles.css` (1,473 lines)**:
   - 100% self-contained CSS implementing Caribbean Nautical design system (`--slate-900: #0f172a`, `--teal-600: #0d9488`, `--amber-500: #f59e0b`, `--whatsapp: #25d366`).
   - Zero remote fonts or framework imports. Fully responsive with mobile, tablet, and desktop breakpoints.

4. **`web/app.js` (1,276 lines)**:
   - Authentic search engine using Spanish diacritics stripping (`normalize('NFD').replace(/[\u0300-\u036f]/g, '')`).
   - Pre-computed `_searchBlob` on all 172 records for <1ms multi-token conjunction search.
   - Dynamic multi-faceted filtering matching `ORIGINAL_REQUEST.md` §R2 criteria.
   - Real dual-layer persistence: immediate local `localStorage` optimistic state + debounced 300ms network sync via `POST /api/tracking`.
   - Colombian WhatsApp link generator with country code prefix `57` and prefilled inquiry message referencing property ID.

### 1.2 Runtime Test Execution Observations

1. **Dashboard Test Suite**:
   ```bash
   python -m unittest tests/test_dashboard.py
   ```
   *Result:*
   ```
   .................
   ----------------------------------------------------------------------
   Ran 17 tests in 1.192s

   OK
   ```
   All 17 tests passed cleanly.

2. **Full Repository Test Suite**:
   ```bash
   python -m unittest discover tests
   ```
   *Result:*
   ```
   Ran 94 tests in 7.909s
   FAILED (failures=3)
   ```
   All existing pipeline and dashboard tests pass (84 tests). The 3 failures stem from the newly introduced adversarial suite `tests/test_adversarial_m2.py` created by `challenger_m2_1`.

### 1.3 Persistence Integrity Independent Verification

We executed an independent, opaque-box empirical persistence test:
1. Started `run_dashboard.py` server instance 1.
2. Dispatched `POST /api/tracking` with:
   ```json
   {
     "property_id": "AUDIT-LIVE-TEST-001",
     "status": "visita_programada",
     "favorite": true,
     "notes": "Live test note",
     "rating": 4
   }
   ```
   Response: `HTTP 200 OK`, `{"success": true}`.
3. Inspected `data/user_tracking.json` on disk: record physically written with `updated_at` timestamp.
4. Forcefully terminated (killed) server instance 1 process. Verified connection refused.
5. Started a brand new `run_dashboard.py` server instance 2 on a different port.
6. Executed `GET /api/tracking` against server 2.
   *Result:* `AUDIT-LIVE-TEST-001` retrieved immediately with status `visita_programada`, rating `4`, and notes intact.
7. Cleaned test record from `data/user_tracking.json` and terminated server 2 cleanly.

### 1.4 Runtime Defect Observations (Crucial Findings)

#### Defect 1: Windows Console Startup Crash (`UnicodeEncodeError`)
- **Location**: `run_dashboard.py`, line 390:
  ```python
  390: print("  🏢 TRACKER DE APARTAMENTOS Y CASAS EN ARRIENDO - BARRANQUILLA NORTE")
  ```
- **Execution Command**:
  ```powershell
  python run_dashboard.py --no-browser --port 8765
  ```
  or running `start_dashboard.bat`:
  ```cmd
  start_dashboard.bat
  ```
- **Verbatim Error**:
  ```
  Traceback (most recent call last):
    File "C:\Users\Admin\Downloads\TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR\run_dashboard.py", line 419, in <module>
      main()
    File "C:\Users\Admin\Downloads\TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR\run_dashboard.py", line 390, in main
      print("  \U0001f3e2 TRACKER DE APARTAMENTOS Y CASAS EN ARRIENDO - BARRANQUILLA NORTE")
    File "C:\Users\Admin\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\Lib\encodings\cp1252.py", line 19, in encode
      return codecs.charmap_encode(input,self.errors,encoding_table)[0]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f3e2' in position 2: character maps to <undefined>
  [AVISO] El servidor se detuvo con codigo de error 1.
  ```
- **Cause**: On Windows consoles using standard code page `cp1252`, `sys.stdout` cannot encode the `🏢` emoji (`\U0001f3e2`). The server crashes before opening sockets.

#### Defect 2: Unhandled Malformed Payloads in `POST /api/tracking` (From Challenger Suite)
- In `run_dashboard.py` lines 320-341:
  1. Sending non-UTF-8 bytes raises `UnicodeDecodeError` in `raw_body.decode('utf-8')`, caught as generic `Exception` and returned as **HTTP 500** instead of **HTTP 400**.
  2. Sending non-dictionary JSON (e.g. integer `12345`) causes `TypeError` in `"property_id" in payload`, returned as **HTTP 500** instead of **HTTP 400**.

#### Defect 3: Windows Socket Hijacking with `allow_reuse_address = True` (From Challenger Suite)
- In `run_dashboard.py` line 348:
  On Windows Winsock, `SO_REUSEADDR` allows two instances of `ReusableThreadingServer` to bind to the same port simultaneously without raising `OSError`, bypassing the auto-increment fallback.

---

## 2. Logic Chain

1. **Integrity Evaluation**:
   - R1 & R2 specifications require an interactive local web dashboard with real search, filtering, card grid, and persistent state tracking.
   - Static analysis of `web/app.js`, `web/index.html`, and `run_dashboard.py` shows complete, authentic, zero-dependency implementations. There are no stubbed functions, mock return constants, bypass flags, or hardcoded test assertions.
   - `tests/test_dashboard.py` exercises genuine HTTP requests over live sockets and inspects the filesystem.
   - Therefore, the codebase is free of cheating, fakery, and prohibited integrity patterns under Development Mode (`CLEAN`).

2. **Runtime Execution & Persistence Evaluation**:
   - `python -m unittest tests/test_dashboard.py` completes 17/17 tests with `OK`.
   - Independent opaque-box restart testing proved that data written via `POST /api/tracking` persists on disk and reloads cleanly in subsequent server sessions.
   - Therefore, persistence integrity is mathematically and empirically validated.

3. **Defect Causality Evaluation**:
   - `test_dashboard.py` passed because it directly calls `create_server()` and does not invoke `main()`, avoiding the banner `print()` on line 390.
   - When a real Windows user runs `start_dashboard.bat` or `python run_dashboard.py`, the default Windows terminal encoding (`cp1252`) cannot encode `🏢`, causing an unhandled crash.
   - This defect does not represent malicious intent or integrity fraud, but is a severe runtime blocker on Windows that must be fixed by worker_m2_1 before marking Milestone 2 fully operational.

---

## 3. Caveats

- **Scope Boundary**: This audit investigated Milestone 2 components (`run_dashboard.py`, `web/`, `start_dashboard.bat`, `tests/test_dashboard.py`, and `data/user_tracking.json`). It did not re-audit M1 extractor web scrapers.
- **Audit Rule Constraint**: As a Forensic Auditor, per team protocol, we do NOT modify implementation code directly. Fixes must be assigned to worker agents.

---

## 4. Conclusion

1. **Integrity Verdict**: **`CLEAN`**.
   - No hardcoded test responses.
   - No facade or dummy implementations.
   - No fabricated verification logs.
   - Authentic, complete, zero-dependency implementation of all R2 requirements.
   - State persistence across sessions verified 100%.

2. **Remediation Required Before M2 Closure**:
   - **Fix 1 (Windows CLI Crash)**: In `run_dashboard.py`, add `sys.stdout.reconfigure(encoding="utf-8")` at the top of `main()` or replace the `🏢` emoji with an ASCII-safe character (e.g. `[APP]`), and in `start_dashboard.bat`, add `chcp 65001 >nul 2>&1` and `set PYTHONIOENCODING=utf-8`.
   - **Fix 2 (HTTP 400 on Malformed Input)**: In `run_dashboard.py` `do_POST`, wrap body decoding in `try ... except UnicodeDecodeError` and validate `if not isinstance(payload, dict): self.send_error(400, "Expected JSON object")`.
   - **Fix 3 (Windows Port Contention)**: In `ReusableThreadingServer`, avoid setting `allow_reuse_address = True` on Windows (`if sys.platform != 'win32': allow_reuse_address = True`).

---

## 5. Verification Method

To independently reproduce all observations:

1. **Verify Integrity Test Suite (17/17 Passing)**:
   ```powershell
   python -m unittest tests/test_dashboard.py
   ```
   *Expected:* 17 tests pass with `OK`.

2. **Reproduce Windows Console Startup Crash**:
   ```powershell
   python run_dashboard.py --no-browser --port 8765
   ```
   *Expected:* Crashes immediately with `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f3e2'`.

3. **Verify Server Functionality with UTF-8 Console**:
   ```powershell
   $env:PYTHONIOENCODING="utf-8"
   python run_dashboard.py --no-browser --port 8765
   ```
   *Expected:* Server starts and serves `http://127.0.0.1:8765/` without errors.

4. **Verify Cross-Session Persistence**:
   Execute the test script in section 1.3 to confirm data persists across independent server process lifetimes.
