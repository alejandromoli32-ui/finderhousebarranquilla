## 2026-09-13T22:20:57Z
You are worker_m1_2, an implementation worker subagent for Milestone 1 Remediation (M1 Iteration 2).
Your Working Directory is: c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/worker_m1_2
Your parent is orchestrator_1 (conversation ID: 78e1bffd-c00b-4edf-9b66-26fc5574a726).

MANDATORY FIRST STEP: Read:
1. c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/ORIGINAL_REQUEST.md
2. c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/orchestrator_1/PROJECT.md
3. c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/explorer_m1_retry_1/analysis.md and handoff.md
4. c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/explorer_m1_retry_2/analysis.md and handoff.md
5. c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR/.agents/explorer_m1_retry_3/analysis.md and handoff.md

YOUR EXCLUSIVE WRITE OWNERSHIP:
- data_pipeline/pipeline.py
- data_pipeline/deduplicator.py
- tests/test_adversarial_dedup_geo.py
- data/inmuebles_barranquilla.json
- data/inmuebles_barranquilla.csv

YOUR MISSION:
1. Implement the Geographic Boundary Filtering fix in `data_pipeline/pipeline.py`:
   - Conjunction gate: Ensure listings in Puerto Colombia / Soledad / outside Barranquilla are rejected.
   - Ensure neighborhood matching uses ALLOWED_BARRIOS and NEIGHBORHOOD_SYNONYMS.
2. Implement Schema Invariant Sanitization:
   - In `data_pipeline/pipeline.py` and `data_pipeline/deduplicator.py`:
     - Stratum: sanitize `1 <= stratum <= 6`; otherwise set to `None` (`null` in JSON).
     - Bedrooms: clamp `max(0, bedrooms)` (so `-1` becomes `0`).
3. Implement Interface Contract Zone Invariant:
   - Ensure every listing's `zone` is strictly `"Norte"` or `"Noroccidente"`. Map `Ciudad Mallorquin` to `"Noroccidente"` and eliminate any `"Otros"`.
4. Update `tests/test_adversarial_dedup_geo.py`:
   - Update expected record count from 173 to 172 (accounting for the purged Puerto Colombia listing).
   - Verify that all assertions for stratum (allowing None or 1..6) and bedrooms (>= 0) are satisfied.
5. Re-run pipeline and run all test suites:
   - Run `python -m data_pipeline.pipeline` to regenerate `data/inmuebles_barranquilla.json` and `data/inmuebles_barranquilla.csv`.
   - Run `python -m unittest tests/test_adversarial_dedup_geo.py` (all 21 tests must pass).
   - Run `python -m unittest tests/test_pipeline.py` (all 21 tests must pass).
   - Run `python -m unittest tests/test_adversarial_m1.py` (all 25 tests must pass).
