# Adversarial Challenge Report: Milestone 2 Frontend Filtering Logic and Edge Cases

**Author**: challenger_m2_2 (Empirical Challenger)  
**Target Component**: `web/app.js`, `web/index.html`, `data/inmuebles_barranquilla.json`  
**Verdict**: **APPROVE**  
**Date**: 2026-09-13  

---

## 1. Observation

Direct empirical observations collected from the codebase, test execution, and benchmark measurements:

### A. Source Implementation in `web/app.js`
1. **Normalization Function** (`web/app.js:144-152`):
   ```javascript
   function normalizeText(str) {
     if (!str) return '';
     return str
       .toString()
       .normalize('NFD')
       .replace(/[\u0300-\u036f]/g, '')
       .toLowerCase()
       .trim();
   }
   ```
2. **Pre-computed In-Memory Search Blob** (`web/app.js:324-339`):
   ```javascript
   state.properties.forEach(p => {
     const parts = [
       p.title || '',
       p.neighborhood || '',
       p.zone || '',
       p.property_type || '',
       p.address || '',
       p.contact?.agency || '',
       p.contact?.agent_name || '',
       p.contact?.phone || '',
       p.contact?.whatsapp || '',
       p.description || '',
       p.id || ''
     ];
     p._searchBlob = normalizeText(parts.join(' '));
   });
   ```
3. **Multi-Token Conjunction Matching** (`web/app.js:406, 463-469`):
   ```javascript
   const tokens = query ? normalizeText(query).split(/\s+/).filter(Boolean) : [];
   ...
   if (tokens.length > 0) {
     for (let i = 0; i < tokens.length; i++) {
       if (!p._searchBlob.includes(tokens[i])) {
         return false;
       }
     }
   }
   ```
4. **Price Ceiling Enforcement & Empty State Trigger** (`web/app.js:428, 503-509`):
   ```javascript
   if (p.total_price > maxPrice) return false;
   ...
   if (list.length === 0) {
     el.propertyGrid.innerHTML = '';
     el.emptyState.style.display = 'block';
     return;
   }
   el.emptyState.style.display = 'none';
   ```

### B. Empirical Test Execution Results
Executed via `node tests/test_adversarial_filtering.js` and `python -m unittest tests/test_adversarial_m2_filtering.py`:
- **Total Assertions**: 30
- **Passed**: 30
- **Failed**: 0
- **Verbatim Benchmark Output**:
  ```
  --- BENCHMARK RESULTS (1000 executions) ---
  Total execution time : 247.18 ms
  Average latency      : 0.2469 ms
  Median (P50) latency : 0.1519 ms
  95th Percentile (P95): 0.7793 ms
  99th Percentile (P99): 1.5559 ms
  Min latency          : 0.0157 ms
  Max latency          : 3.3593 ms

  [PASS] Performance Benchmark: Average Latency < 10ms: Average latency is 0.2469 ms (Target: < 10.0 ms)
  [PASS] Performance Benchmark: P95 Latency < 10ms: P95 latency is 0.7793 ms (Target: < 10.0 ms)
  [PASS] Performance Benchmark: P99 Latency < 25ms: P99 latency is 1.5559 ms
  ```

---

## 2. Logic Chain

1. **Diacritics & Fuzziness Equivalence**:
   - In Spanish, letters with acute accents (á, é, í, ó, ú) and tildes (ñ) represent common search inputs.
   - Observation 1 demonstrates that `normalizeText()` applies Unicode canonical decomposition (`normalize('NFD')`) followed by stripping the Combining Diacritical Marks block (`[\u0300-\u036f]`).
   - Empirically, queries `"paraiso"` and `"Paraíso"` both returned exactly 18 properties; `"riomar"` and `"RÍOMAR"` both returned 23 properties; `"cúcuta"` and `"cucuta"` both returned 0 properties without throwing; and `"ñ"` executed without crashing.
   - Observation 3 shows search uses substring matching via `String.prototype.includes(token)` on the tokenized string, rather than compiling a dynamic `new RegExp(token)`.
   - Consequently, unescaped regex meta-characters (`[`, `]`, `(`, `)`, `*`, `+`, `?`, `\`, `^`, `$`, `|`), quotation marks (`"`, `'`), and injection strings (`<script>`, `' OR 1=1`) cannot cause `SyntaxError: Invalid regular expression` or injection vulnerabilities. All 20 adversarial payloads were evaluated with 0 exceptions.

2. **Extreme Filter Bounds & Empty State Handling**:
   - The verified database (`data/inmuebles_barranquilla.json`) contains 172 records with prices ranging from $1.100.000 COP to $2.500.000 COP.
   - Setting `maxPrice = 500000` COP strictly evaluates `p.total_price > maxPrice`, resulting in 0 matches.
   - Observation 4 confirms that when `list.length === 0`, `propertyGrid.innerHTML` is cleared to empty, `emptyState.style.display` is switched from `'none'` to `'block'`, and the results counter updates to `"Mostrando 0 de 172 inmuebles"`.
   - Invoking `emptyResetBtn.click()` restores `maxPrice` to $2.500.000 COP, sets `emptyState.style.display` back to `'none'`, and restores all 172 properties.
   - Setting `maxPrice = 2500000` COP keeps all 172 properties active because all inventory satisfies the project price ceiling rule ($2.5M COP).

3. **Performance Benchmark**:
   - Across 1,000 realistic permutations of text queries, diacritics, barrios, bedrooms, bathrooms, parking, and property types, total elapsed time was 247.18 ms.
   - Average latency was **0.2469 ms**, which is **40.5x faster** than the mandated 10.0 ms threshold.
   - Even the 99th percentile (P99) of 1.5559 ms and absolute maximum of 3.3593 ms remained well beneath the 10.0 ms ceiling.

---

## 3. Caveats

- **Client DOM Simulation**: The automated benchmark ran in Node.js v24 using a standard event-driven DOM sandbox that mirrors modern browser event dispatching and rendering properties. Browser layout re-flow / repaint times were not measured as they depend on the host GPU/display server, though DOM manipulation overhead in `app.js` is minimal due to innerHTML batching.
- **Backend Port Collision Findings**: During test discovery, 3 failures were detected in `tests/test_adversarial_m2.py` (authored by peer agent testing server error handling in `run_dashboard.py`). Those are backend server findings outside this agent's frontend review scope and do not impair the client-side filtering algorithms in `web/app.js`.

---

## 4. Conclusion

The Milestone 2 Frontend Filtering Logic and Edge Cases in `web/app.js` satisfy and exceed all specification criteria:
- Diacritics and fuzzy token normalization are fully symmetric and robust against Spanish accents and ñ.
- Adversarial inputs (quotes, brackets, regex characters, XSS/SQLi strings) execute with zero unhandled exceptions.
- Extreme bounds ($500.000 COP and $2.500.000 COP) correctly manage empty states and full inventory restoration.
- Real-time search and filter latency averages ~0.25 ms per query, far exceeding the 10ms performance SLA.

**Verdict**: **APPROVE**

---

## 5. Verification Method

To independently execute and verify the empirical adversarial findings:

```bash
# 1. Run Node.js In-Memory DOM Adversarial Suite and 1000-run Benchmark:
node tests/test_adversarial_filtering.js

# 2. Run Python Unittest Integration Runner:
python -m unittest tests/test_adversarial_m2_filtering.py
```

### Invalidation Conditions
- Any test assertion failure in `tests/test_adversarial_filtering.js` (e.g. `testResults.failed > 0`).
- Average latency exceeding 10.0 ms across 1,000 simulated filter executions.
- Unhandled `SyntaxError` when typing `[`, `(`, or quotes into `searchInput`.
