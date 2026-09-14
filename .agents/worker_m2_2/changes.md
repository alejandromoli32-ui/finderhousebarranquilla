# Changes Implemented by worker_m2_2 (M2 Remediation)

## 1. `run_dashboard.py`
- **Stream Encoding Configuration**: Added `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` and `sys.stderr.reconfigure(encoding='utf-8', errors='replace')` at the module header and in `main()` to protect against `UnicodeEncodeError` under Windows console codepages (cp1252, cp437).
- **Clean ASCII Banner Tags**: Replaced terminal emoji (`🏢`) with clean ASCII tags (`[TRACKER]`, `[PORT]`, `[OK]`, `[INFO]`, `[BROWSER]`) with `flush=True` on all console outputs.
- **Configurable Persistence Path & Dynamic Proxy**:
  - Implemented `get_tracking_file_path()`, `set_tracking_file_path()`, and `TRACKING_STORE_PATH` / `TRACKING_FILE` environment variable support.
  - Implemented `_TrackingFileProxy(os.PathLike)` so that existing imports of `TRACKING_FILE` dynamically resolve to the active tracking file path without cache staleness.
  - Added `target_path.parent.mkdir(parents=True, exist_ok=True)` in `save_tracking_data_locked()`.
- **Payload Validation & Error Handling in `POST /api/tracking`**:
  - Added `_send_json_error(self, code: int, error_msg: str)` to emit RFC-compliant JSON error responses.
  - Validated `Content-Length` integer conversion (`try...except (ValueError, TypeError)` -> HTTP 400).
  - Empty body check (`content_length <= 0` -> HTTP 400 with `{"error": "Empty payload"}`).
  - Wrapped `raw_body.decode('utf-8')` in `try...except (UnicodeDecodeError, Exception)` -> HTTP 400 with `{"error": "Invalid UTF-8 payload"}`.
  - Validated JSON decoding -> HTTP 400 with `{"error": "Invalid JSON in request body"}`.
  - Added strict dictionary validation (`if not isinstance(payload, dict)` -> HTTP 400 with `{"error": "Payload must be a JSON object"}`).
  - Added type check in `update_tracking_state(payload)` and wrapped in `try...except Exception` in handler -> HTTP 400 with `{"error": f"Error processing tracking update: {e}"}`.
  - Removed dead debug ternary (`raw_body = self.wfile.write if False else self.rfile.read(...)`).
- **Windows Socket Hijacking & Port Conflict Remediation**:
  - In `ReusableThreadingServer`: on `sys.platform == 'win32'`, disabled address reuse (`allow_reuse_address = False`) and set `SO_EXCLUSIVEADDRUSE` on `server_bind()`.
  - In `find_free_port`: on Win32, set `SO_EXCLUSIVEADDRUSE` to avoid false availability reports.
  - In `create_server`: supported `port == 0` binding to ephemeral free port, returning `server.server_address[1]`.
- **Restricted Static File Serving**:
  - Enforced strict routing within `WEB_DIR`.
  - Stripped fallback to `BASE_DIR / clean_rel`, preventing exposure of root source files (`run_dashboard.py`, `start_dashboard.bat`, `.agents/`, etc.).
  - Explicit routes for `/api/properties`, `/data/inmuebles_barranquilla.json`, and `/data/inmuebles_barranquilla.csv` remain active.

## 2. `start_dashboard.bat`
- Added `chcp 65001 >nul` to force Windows command prompt codepage to UTF-8.
- Added `set PYTHONUTF8=1` and `set PYTHONIOENCODING=utf-8` to ensure child Python processes use UTF-8 by default.
- Replaced emoji `🏢` with ASCII tag `[TRACKER]` and status tags `[INFO]`.

## 3. `data/user_tracking.json`
- Restored persistence store to pristine default state:
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
- All leftover test records (`CONCURRENT-PROP-*`, `STRESS-*`, `AUDIT-LIVE-*`, `FR-TEST-*`) were purged.

## 4. `tests/test_dashboard.py`
- Added tracking store isolation in `setUpClass` using `tempfile.TemporaryDirectory()` and setting `TRACKING_STORE_PATH`, unsetting and cleaning up in `tearDownClass`.
- Added `test_windows_console_startup_cp1252_zero_crash`: Launches `run_dashboard.py --help` and `run_dashboard.py --no-browser --port 0` with `PYTHONIOENCODING=cp1252` and `PYTHONUTF8=0` to verify zero `UnicodeEncodeError`.
- Added `test_post_tracking_invalid_utf8_payload`: Verifies HTTP 400 with `Invalid UTF-8 payload`.
- Added `test_post_tracking_non_dict_payload`: Verifies HTTP 400 with `Payload must be a JSON object` for scalars, arrays, booleans, and null.
- Added `test_static_file_serving_restrictions`: Verifies requests to `/run_dashboard.py`, `/start_dashboard.bat`, `/.agents/...`, and `/data/user_tracking.json` return 403 or 404.

## 5. `tests/test_adversarial_m2.py`
- Added tracking store isolation in `setUpClass` using `tempfile.TemporaryDirectory()` and setting `TRACKING_STORE_PATH`, unsetting and cleaning up in `tearDownClass`.
- Guaranteed that adversarial test runs never write to `data/user_tracking.json`.
