## 2026-09-13T22:37:39Z

You are worker_m2_2, an implementation remediation worker for Milestone 2 (M2 Iteration 2).
Your Working Directory is: c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/worker_m2_2
Your parent is orchestrator_1 (conversation ID: 78e1bffd-c00b-4edf-9b66-26fc5574a726).

MANDATORY FIRST STEP: Read:
1. c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/ORIGINAL_REQUEST.md
2. c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/orchestrator_1/PROJECT.md
3. c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/reviewer_m2_1/handoff.md
4. c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/reviewer_m2_2/handoff.md
5. c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/challenger_m2_1/handoff.md

YOUR EXCLUSIVE WRITE OWNERSHIP:
- run_dashboard.py
- start_dashboard.bat
- tests/test_dashboard.py
- tests/test_adversarial_m2.py
- data/user_tracking.json

YOUR MISSION:
1. Fix Windows Console Startup Crash:
   - In `run_dashboard.py`: Add `if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')` at the top of file and in `main()`.
   - In `run_dashboard.py`: Replace emojis in terminal print strings with clean ASCII tags (e.g. `[TRACKER]`, `[OK]`, `[PORT]`, `[BROWSER]`) to eliminate any chance of `UnicodeEncodeError` under Windows cp1252/cp437 console.
   - In `start_dashboard.bat`: Add `chcp 65001 >nul` and `set PYTHONUTF8=1` before `python run_dashboard.py`.
   - In `tests/test_dashboard.py`: Add a test that invokes `python run_dashboard.py --no-browser --port 0` with `PYTHONIOENCODING=cp1252` to prove zero crash.
2. Fix Malformed Payload Handling in `POST /api/tracking`:
   - In `run_dashboard.py`: Wrap body decoding in `try...except (UnicodeDecodeError, Exception)` -> return HTTP 400 with `{"error": "Invalid UTF-8 payload"}`.
   - Check `isinstance(data, dict)`; if not -> return HTTP 400 with `{"error": "Payload must be a JSON object"}`.
   - Catch any unexpected exception in `update_tracking_state` and return HTTP 400.
3. Fix Windows Socket Collision:
   - In `run_dashboard.py`: On Windows (`sys.platform == 'win32'`), do not set `allow_reuse_address = True`, or use `socket.SO_EXCLUSIVEADDRUSE` if available, so that port 8000 cannot be hijacked and secondary instances detect port in use and smoothly increment to port 8001+.
4. Test Store Isolation & Restore Pristine Default:
   - In `run_dashboard.py`: Support `TRACKING_STORE_PATH` env var or allow configuring tracking file path.
   - In `tests/test_dashboard.py` and `tests/test_adversarial_m2.py`: Use temporary files so tests NEVER write to `data/user_tracking.json`.
   - Restore `data/user_tracking.json` to pristine default: `{"properties": {}}`.
5. Restrict Static File Serving:
   - Only serve files from `web/` and `data/inmuebles_barranquilla.*`. Reject any path attempting to escape or access internal source files.
6. Execution & Verification:
   - Run `python -m unittest tests/test_dashboard.py`
   - Run `python -m unittest tests/test_adversarial_m2.py`
   - Run full discovery: `python -m unittest discover tests` (all tests must pass 100%).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

OUTPUT REQUIREMENTS:
Write changes to `changes.md` and handoff report to `handoff.md`.
Include the test output in your report. Send completion message to parent when done.
