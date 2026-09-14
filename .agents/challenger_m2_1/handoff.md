# Handoff Report — Adversarial Testing of Milestone 2 Backend Server & API

**Agent**: `challenger_m2_1`  
**Role**: Empirical Challenger (critic, specialist)  
**Target**: Milestone 2 Backend Server & API (`run_dashboard.py`)  
**Verdict**: **`REJECT`** (Due to unhandled malformed payloads returning HTTP 500/200 instead of HTTP 400, and Windows multi-instance port collision via `allow_reuse_address = True`)

---

## 1. Observation

### 1.1 Test Execution Commands & Outputs
- **Test Suite Executed**: `python -m unittest tests/test_adversarial_m2.py -v`
- **Result**: `Ran 10 tests in 5.671s — FAILED (failures=3)`
  - `test_concurrency_20_threads_no_dropped_keys`: **OK**
  - `test_concurrency_race_condition_updates_same_key`: **OK**
  - `test_concurrency_mixed_read_write_stress`: **OK**
  - `test_empty_payload`: **OK**
  - `test_malformed_invalid_json_syntax`: **OK**
  - `test_port_contention_port_8000_fallback`: **OK** (Standard socket)
  - `test_port_contention_consecutive_occupied_ports`: **OK**
  - `test_malformed_invalid_utf8_bytes`: **FAIL** (Expected HTTP 400, got HTTP 500)
  - `test_malformed_non_dictionary_bodies`: **FAIL** (Expected HTTP 400, got HTTP 500 or HTTP 200)
  - `test_port_contention_dual_dashboard_windows_collision`: **FAIL** (Expected port increment, got collision on 8000)

### 1.2 Verbatim Errors & Diagnostic Observations

#### Observation 1: Invalid UTF-8 Bytes Trigger HTTP 500
- **File**: `run_dashboard.py`, lines 320-341:
```python
320: raw_body = self.wfile.write if False else self.rfile.read(content_length)
321: payload = json.loads(raw_body.decode("utf-8"))
...
337: except json.JSONDecodeError:
338:     self.send_error(400, "Invalid JSON in request body")
339: except Exception as e:
340:     self.send_error(500, f"Error processing tracking update: {e}")
```
- **Execution**: Sending `b'\xff\xfe\xfa\x00'` or `b'\x80\x81\x82'` causes `raw_body.decode("utf-8")` to raise `UnicodeDecodeError`.
- **Verbatim Error**:
```
AssertionError: 500 != 400 : Invalid UTF-8 sample b'\xff\xfe\xfa\x00' produced status 500 instead of 400.
Body: Message: Error processing tracking update: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte.
```

#### Observation 2: Non-Dictionary JSON Payloads Trigger HTTP 500 or HTTP 200
- **File**: `run_dashboard.py`, lines 82-106 & line 323:
```python
88: if "property_id" in payload:
...
106: elif "properties" in payload and isinstance(payload["properties"], dict):
```
- **Execution with integer/boolean/null/float**:
  - Sending `b"12345"`, `b"true"`, `b"null"`, `b"3.14159"`, or `b"NaN"`:
  - `json.loads` parses successfully.
  - Line 88 executes `"property_id" in payload`.
  - In Python, membership tests on non-iterable scalars raise `TypeError`.
  - Line 340 catches `TypeError` and emits HTTP 500:
  ```
  AssertionError: 500 != 400 : Non-dictionary body (integer: b'12345') produced status 500 instead of 400.
  Body: Message: Error processing tracking update: argument of type 'int' is not iterable.
  ```
- **Execution with strings and arrays**:
  - Sending `b'"hello string"'` or `b'[1, 2, 3]'`:
  - Line 88 evaluates to `False`. Line 106 evaluates to `False`.
  - The server ignores the payload, saves tracking data, and returns **HTTP 200 OK** (`{"success": true}`) instead of rejecting malformed non-dictionary input with **HTTP 400 Bad Request**.

#### Observation 3: High-Concurrency (20 Threads) Passes Completely
- **File**: `run_dashboard.py`, lines 30, 46-80:
```python
30: _TRACKING_LOCK = threading.RLock()
...
71: def save_tracking_data_locked(data: dict) -> None:
74:     temp_file = TRACKING_FILE.with_suffix(".json.tmp")
...
79:     os.replace(temp_file, TRACKING_FILE)
```
- **Execution**: 20 threads simultaneously writing 100 distinct properties synchronized with `threading.Barrier`:
  - 100 requests executed in 1.815s.
  - 0 dropped keys (all 100 expected property IDs persisted in `data/user_tracking.json`).
  - 0 JSON corruption events.
  - 20 threads simultaneously updating the exact same property key: 0 corruption, state consistently maintained.
  - Concurrent mixed reads (`GET /api/tracking`) and writes: 0 read errors, 0 partial reads.

#### Observation 4: Windows Socket Reuse Collision
- **File**: `run_dashboard.py`, lines 346-350:
```python
346: class ReusableThreadingServer(http.server.ThreadingHTTPServer):
347:     """Threading HTTP server with address reuse enabled."""
348:     allow_reuse_address = True
349:     daemon_threads = True
```
- **Execution**:
  - When a standard socket occupies port 8000, `create_server(port=8000)` detects `OSError` and increments to 8001.
  - However, when two instances of `run_dashboard.py` (or two servers setting `SO_REUSEADDR`) run on Windows:
    - Server 1 binds to 8000.
    - Server 2 ALSO binds to 8000 (both return port 8000 without error).
    - Windows Winsock permits socket hijacking when `SO_REUSEADDR` is active without `SO_EXCLUSIVEADDRUSE`.

---

## 2. Logic Chain

1. **Mission Mandate**: The specification explicitly states:
   > "Malformed payloads: invalid JSON strings, non-dictionary bodies, invalid UTF-8 bytes. Verify server responds with HTTP 400 without crashing."
2. **Observation 1 & 2**:
   - For invalid UTF-8 bytes, the server raises `UnicodeDecodeError`, which is unhandled in the HTTP 400 handler and caught by the generic `except Exception` block, returning HTTP 500.
   - For non-dictionary JSON scalars (`int`, `bool`, `null`, `float`, `NaN`), `update_tracking_state` assumes `payload` is a dictionary or iterable of keys. It raises `TypeError`, returning HTTP 500.
   - For non-dictionary JSON iterables (`str`, `list`), the server silently swallows the request and responds with HTTP 200 OK.
   - While the server remains running (does not terminate), returning HTTP 500 or HTTP 200 for malformed client inputs violates RFC 9110 HTTP semantics (client errors must be 4xx, specifically 400 Bad Request) and directly violates the mission acceptance criteria.
3. **Observation 4**:
   - On Windows, `allow_reuse_address = True` (`SO_REUSEADDR`) does not prevent port conflicts across multiple server instances; instead, it causes silent port sharing/hijacking. If a user launches `start_dashboard.bat` twice, both servers bind to 8000.
4. **Conclusion**:
   - While the concurrency layer is rock-solid (Observation 3), Milestone 2 cannot be approved in its current state due to the malformed payload handling failures and Windows port collision risk. The verdict is **REJECT**.

---

## 3. Caveats

- **Load limit**: Concurrency was tested up to 20 parallel threads (100 requests in ~1.8s) and mixed read/write loads as specified. Workloads exceeding 100+ concurrent threads or payloads > 10MB were not tested.
- **Platform Scope**: Port collision via `SO_REUSEADDR` is specific to Windows Winsock semantics. On POSIX (Linux/macOS), `SO_REUSEADDR` behaves differently for active listeners. However, since the user environment is explicitly Windows, this vulnerability is real and impactful.

---

## 4. Conclusion & Actionable Fixes

**Verdict**: **`REJECT`**

### Required Remediations for Milestone 2 Worker:
1. **Fix `do_POST` in `run_dashboard.py`**:
   - Add explicit decoding error handling:
     ```python
     try:
         decoded_body = raw_body.decode("utf-8")
     except UnicodeDecodeError:
         self.send_error(400, "Invalid UTF-8 encoding in request body")
         return
     ```
   - Enforce dictionary payload requirement immediately after JSON parsing:
     ```python
     try:
         payload = json.loads(decoded_body)
     except (json.JSONDecodeError, ValueError):
         self.send_error(400, "Invalid JSON in request body")
         return

     if not isinstance(payload, dict):
         self.send_error(400, "Request body must be a JSON object")
         return
     ```
2. **Fix Windows Port Conflict Handling**:
   - Either disable `allow_reuse_address = False` on Windows (or conditionally when `sys.platform == "win32"`), or explicitly verify port availability using a dedicated non-reusable probe before binding `ReusableThreadingServer`.

---

## 5. Verification Method

To independently verify these findings, run the following commands in powershell from the project root:

1. **Run full adversarial test suite**:
   ```bash
   python -m unittest tests/test_adversarial_m2.py -v
   ```
   *Expect*: 7 passing tests, 3 reproducible assertion failures (`test_malformed_invalid_utf8_bytes`, `test_malformed_non_dictionary_bodies`, `test_port_contention_dual_dashboard_windows_collision`).

2. **Run empirical benchmark and status matrix report**:
   ```bash
   python -m tests.run_adversarial_benchmark
   ```
   *Inspect*: Generated report in console and `data/adversarial_benchmark_results.json`.

3. **Verify concurrency safety**:
   ```bash
   python -m unittest tests.test_adversarial_m2.TestAdversarialM2Server.test_concurrency_20_threads_no_dropped_keys
   ```
   *Expect*: OK (100 distinct keys written across 20 parallel threads with zero data loss).
