# Review & Adversarial Audit Report: Milestone 2 (M2)

**Reviewer:** `reviewer_m2_2` (Reviewer & Adversarial Critic)  
**Parent:** `orchestrator_1` (Conversation ID: `78e1bffd-c00b-4edf-9b66-26fc5574a726`)  
**Milestone:** M2 — Backend Server & Persistence Engine  
**Date:** 2026-09-13  
**Verdict:** **REQUEST_CHANGES**

---

## 1. Observation

1. **Automated Test Results**:
   - Running `python -m unittest tests/test_dashboard.py -v`:
     `Ran 17 tests in 1.213s. OK.`
   - Running `python -m unittest discover tests -v`:
     `Ran 84 tests in 1.747s. OK.`
   - However, inspection of `tests/test_dashboard.py` revealed that tests exclusively invoke `create_server()` in a background thread. **`main()` and the Windows CLI startup sequence were never tested by automated tests.**

2. **Windows Startup Crash (`start_dashboard.bat` and `run_dashboard.py`)**:
   - Running `cmd.exe /c "start_dashboard.bat --no-browser"` or `cmd.exe /c "python run_dashboard.py --no-browser"` failed immediately with exit code 1.
   - Verbatim stdout/stderr output:
     ```
     ======================================================================
       🏢 TRACKER DE APARTAMENTOS Y CASAS EN ARRIENDO - BARRANQUILLA NORTE
       Presupuesto Maximo: $2.500.000 COP (Canon + Administracion)
     ======================================================================

     Iniciando servidor local y abriendo el dashboard en su navegador...
     Para detener el servidor, cierre esta ventana o presione Ctrl+C.

     ======================================================================
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
     Presione una tecla para continuar . . .
     ```
   - Running with `PYTHONUTF8=1` resolved the crash, confirming the failure is caused by printing a 4-byte emoji (`🏢`) on Windows consoles with the default `cp1252` encoding.

3. **Persistence File State & Test Pollution (`data/user_tracking.json`)**:
   - `data/user_tracking.json` currently contains 140 lines populated with test records:
     - Properties: `CONCURRENT-PROP-0` through `CONCURRENT-PROP-9`, `FR-TEST-PERSIST-001`, `FR-TEST-DISCARD-002`.
     - Favorites: 11 test IDs.
     - Notes: 12 test notes.
   - In `tests/test_dashboard.py`, `TestDashboardServer.setUpClass` backs up `TRACKING_FILE` and `tearDownClass` restores it. However, because tests write directly to `data/user_tracking.json`, any interrupted test run leaves residual test data on disk, and subsequent runs restore the polluted state.

4. **Non-Dict Payloads on `POST /api/tracking`**:
   - Sending `POST /api/tracking` with `null`, `12345`, or a non-dict JSON body raises `TypeError: argument of type 'NoneType' is not iterable` in `update_tracking_state()` and returns `HTTP 500` instead of `HTTP 400 Bad Request`.
   - Sending a non-numeric `Content-Length: abc` raises `ValueError` and returns `HTTP 500`.

5. **Static File Path Resolution Boundary (`run_dashboard.py`)**:
   - In lines 258-272 of `run_dashboard.py`:
     ```python
     candidate_base = BASE_DIR / clean_rel
     if candidate_web.exists() and candidate_web.is_file():
         target_file = candidate_web
     elif candidate_base.exists() and candidate_base.is_file():
         target_file = candidate_base
     ```
     and line 270:
     ```python
     if not (resolved_target.is_relative_to(WEB_DIR) or resolved_target.is_relative_to(BASE_DIR)):
     ```
   - An HTTP GET request to `/run_dashboard.py` or `/.agents/orchestrator_1/PROJECT.md` successfully returns `HTTP 200` with the contents of the Python source code or agent metadata.

6. **Adversarial Concurrency Stress Testing**:
   - Tested 50 simultaneous threads issuing `POST /api/tracking` requests under load: 50/50 completed in 1.06s with 0 errors. Thread safety via `_TRACKING_LOCK` and atomic replacement via `os.replace` is robust.
   - Tested port conflict resolution and port exhaustion: auto-increment binds to next available port, and `RuntimeError` is correctly raised when max attempts are exceeded.

---

## 2. Logic Chain

1. **From Observation 2 (Fatal Startup Crash)**:
   - The user requested a Windows-compatible local server and 1-click launcher (`start_dashboard.bat`).
   - Standard Windows environments default to code page 1252 for console output.
   - `run_dashboard.py` line 390 prints `🏢` unconditionally.
   - Because stdout encoding is neither reconfigured nor guarded in `run_dashboard.py`, and `start_dashboard.bat` does not set `PYTHONUTF8=1` or `chcp 65001`, invoking the launcher crashes before binding the server socket.
   - Therefore, the 1-click Windows launcher is non-functional in standard Windows environments.

2. **From Observation 1 & 3 (Test Gap & Store Pollution)**:
   - `test_dashboard.py` did not include CLI execution tests, allowing the encoding crash in `main()` to go undetected.
   - Furthermore, `test_dashboard.py` points directly at `data/user_tracking.json`. When tests run, the production store is mutated. Test records (`CONCURRENT-PROP-...`) are currently committed to the persistence file, contaminating the initial user experience.

3. **From Observation 4 & 5 (Error Handling & Security Boundary)**:
   - Malformed client requests should return 4xx client errors, not 500 server crashes.
   - Static asset serving should be confined to `web/` to adhere to the principle of least privilege, rather than exposing internal repository files in `BASE_DIR`.

---

## 3. Findings

### [Critical] Finding 1: Fatal Crash on Windows Startup (`UnicodeEncodeError` in `run_dashboard.py` line 390)
- **What**: `run_dashboard.py` line 390 prints character `🏢` (`\U0001f3e2`). In standard Windows console / batch executions, this triggers:
  `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f3e2' in position 2: character maps to <undefined>`.
- **Where**: `run_dashboard.py` (line 390), `start_dashboard.bat`.
- **Why**: Windows ANSI codepages (cp1252) cannot encode 4-byte Unicode emojis without explicit UTF-8 encoding configuration.
- **Blast Radius**: `start_dashboard.bat` and CLI `python run_dashboard.py` fail immediately with exit code 1.
- **Fix Recommendation**:
  1. In `run_dashboard.py`: Configure safe encoding at entry:
     ```python
     if sys.platform == "win32":
         try:
             sys.stdout.reconfigure(encoding="utf-8", errors="replace")
             sys.stderr.reconfigure(encoding="utf-8", errors="replace")
         except Exception:
             pass
     ```
     or replace emoji `🏢` with ASCII `[APP]`.
  2. In `start_dashboard.bat`: Add UTF-8 flags before calling Python:
     ```bat
     set PYTHONUTF8=1
     chcp 65001 >nul
     ```
  3. In `tests/test_dashboard.py`: Add CLI invocation tests using `subprocess.run([sys.executable, "run_dashboard.py", "--help"])` and `--no-browser`.

---

### [Major] Finding 2: Test Suite Pollutes Production Persistence Store (`data/user_tracking.json`)
- **What**: Automated tests write test properties (`CONCURRENT-PROP-0` .. `9`, `FR-TEST-PERSIST-001`, `FR-TEST-DISCARD-002`) into `data/user_tracking.json`.
- **Where**: `data/user_tracking.json`, `tests/test_dashboard.py`.
- **Why**: `run_dashboard.py` hardcodes `TRACKING_FILE = DATA_DIR / "user_tracking.json"`. The test suite operates on this file directly.
- **Blast Radius**: A new user opening the dashboard sees mock test properties and test notes in their tracking view.
- **Fix Recommendation**:
  1. Support overriding `TRACKING_FILE` via environment variable or argument:
     ```python
     TRACKING_FILE = Path(os.environ.get("TRACKING_FILE", DATA_DIR / "user_tracking.json"))
     ```
  2. In `tests/test_dashboard.py`, set `os.environ["TRACKING_FILE"]` to a temporary file in a `tempfile.TemporaryDirectory()`.
  3. Clean `data/user_tracking.json` back to its pristine default state:
     ```json
     {
       "version": "1.0",
       "last_updated": "2026-09-13T17:00:00+00:00",
       "properties": {},
       "favorites": [],
       "visits": [],
       "discarded": [],
       "notes": {}
     }
     ```

---

### [Major] Finding 3: HTTP 500 on Non-Dict JSON Body in `POST /api/tracking`
- **What**: Sending a non-dict JSON body (e.g. `null`, `123`) causes `update_tracking_state()` to raise `TypeError` (`argument of type 'NoneType' is not iterable`), returning `HTTP 500`.
- **Where**: `run_dashboard.py` lines 314-341.
- **Why**: `do_POST` assumes `payload` is a dictionary and only catches `JSONDecodeError` as 400.
- **Blast Radius**: Unhandled server exceptions on malformed client requests.
- **Fix Recommendation**:
  Validate payload type in `do_POST`:
  ```python
  if not isinstance(payload, dict):
      self.send_error(400, "Payload must be a JSON object")
      return
  ```
  Wrap `int(self.headers.get("Content-Length", 0))` in `try...except (ValueError, TypeError)` returning 400.

---

### [Minor] Finding 4: Static File Routing Exposes Repository Files from `BASE_DIR`
- **What**: Requesting `/run_dashboard.py` or `/.agents/...` returns internal project files with `HTTP 200`.
- **Where**: `run_dashboard.py` lines 258-272.
- **Why**: Static file lookup falls back to `BASE_DIR / clean_rel` and allows `resolved_target.is_relative_to(BASE_DIR)`.
- **Blast Radius**: Internal code disclosure.
- **Fix Recommendation**:
  Restrict static file serving strictly to `WEB_DIR`. Remove `candidate_base`.

---

### [Minor] Finding 5: Dead Debug Ternary in `run_dashboard.py`
- **What**: Line 320 contains `raw_body = self.wfile.write if False else self.rfile.read(content_length)`.
- **Where**: `run_dashboard.py` line 320.
- **Fix Recommendation**: Clean up to `raw_body = self.rfile.read(content_length)`.

---

## 4. Integrity Check

- **Hardcoded test results**: None. Listings and tracking logic are genuinely computed.
- **Dummy/facade implementation**: None. The server implements genuine `ThreadingHTTPServer`, atomic file replacement, and re-entrant locking.
- **Shortcuts / bypassed tasks**: None. Pure Python standard library used throughout.
- **Fabricated verification logs**: None detected.
- **Self-certifying without independent verification**: The worker relied solely on in-process `unittest` without independently running `start_dashboard.bat` in a native Windows console, allowing the Unicode crash to slip through.

---

## 5. Verified Claims

| Feature / Claim | Verification Method | Status |
|---|---|---|
| Pure standard library implementation | Code inspection of imports | **VERIFIED** |
| `http.server.ThreadingHTTPServer` used | Code inspection of `ReusableThreadingServer` | **VERIFIED** |
| Dynamic port conflict resolution (8000 -> 8001...) | Adversarial port binding stress test | **VERIFIED** |
| `--no-browser` CLI flag | Code inspection & argument parsing verification | **VERIFIED** |
| `GET /api/properties` returns 172 items | HTTP GET inspection & length assertion | **VERIFIED** |
| `GET /data/inmuebles_barranquilla.csv` UTF-8 BOM | Byte-level header and BOM inspection | **VERIFIED** |
| `GET /api/export` (JSON & CSV attachments) | HTTP GET query fuzzing & content validation | **VERIFIED** |
| Concurrency & thread-safety (RLock + atomic replace) | 50 concurrent thread stress test (0 errors) | **VERIFIED** |
| Path traversal protection (`/../../windows/win.ini`) | HTTP GET traversal test (returns 404/403) | **VERIFIED** |
| 1-click Windows launcher (`start_dashboard.bat`) | Subprocess execution in `cmd.exe` | **FAILED (Critical)** |
| Clean user tracking initial store | Inspection of `data/user_tracking.json` | **FAILED (Major)** |

---

## 6. Caveats

- `web/styles.css` visual layout rendering was inspected via CSS rules and HTML structure; full pixel rendering in an interactive browser was not performed in headless mode, but asset loading and MIME types (`text/css`, `image/svg+xml`, `application/javascript`) were verified via HTTP.

---

## 7. Conclusion

Milestone 2 has high code quality, robust concurrency mechanics, and clean architecture. However, because **`start_dashboard.bat` crashes immediately on Windows due to a `UnicodeEncodeError`** and **`data/user_tracking.json` contains leftover test data**, the work product cannot be approved as-is.

**Verdict: REQUEST_CHANGES**

Once Worker M2:
1. Fixes the Windows Unicode console encoding issue in `run_dashboard.py` and `start_dashboard.bat`,
2. Adds automated CLI subprocess tests to `tests/test_dashboard.py`,
3. Isolates test data writes and cleans `data/user_tracking.json`,
4. Validates JSON payload types in `POST /api/tracking` to return 400 instead of 500,
Milestone 2 will be fully production-ready for approval.

---

## 8. Verification Method

To verify the required fixes once applied:

1. **Verify Windows Console & Batch Launch (Must exit 0 or run without UnicodeEncodeError)**:
   ```cmd
   cmd.exe /c "python run_dashboard.py --help"
   cmd.exe /c "start_dashboard.bat --help"
   ```
2. **Verify Server Starts and Responds in Subprocess**:
   ```powershell
   python -c "import subprocess, time, urllib.request; p = subprocess.Popen(['python', 'run_dashboard.py', '--no-browser', '--port', '8995']); time.sleep(1.5); res = urllib.request.urlopen('http://127.0.0.1:8995/api/properties'); print('Status:', res.status); p.terminate(); p.wait()"
   ```
3. **Verify Clean Tracking Store**:
   Inspect `data/user_tracking.json` to ensure `properties` is `{}`.
4. **Run All Unit Tests**:
   ```bash
   python -m unittest discover tests
   ```
