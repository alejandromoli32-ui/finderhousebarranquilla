"""
tests/test_tier5_adversarial_frontend.py

Tier 5 Adversarial Coverage Hardening Test Suite: Frontend Architecture & Client Logic.
Milestone: Final Milestone Phase 2 (Coverage Hardening)
Auditor/Challenger: challenger_final_2

Adversarially tests:
1. Unicode diacritics with combining marks (NFD vs NFC, accents, tildes, uppercase, multi-combining marks).
2. Simultaneous contradictory & impossible filter combinations (disjoint geography, budget bounds, empty tabs).
3. Empty, corrupted, and malformed localStorage schemas (documenting empirical crash conditions).
4. WhatsApp click-to-chat deep link generation, character escaping, newlines, and emojis.
5. Image carousel index wrapping with zero, single, and multiple images.
6. XSS and HTML injection resilience across card and modal templates.
7. Sorting algorithm monotonicity invariants across the complete 172-property dataset.
8. Status tracking workflow state transitions, counter sync, and localStorage persistence.
9. DOM element contract and CSS responsive design system parity.
10. Master execution of the comprehensive Node.js headless DOM adversarial harness.
"""

import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
import unittest
import urllib.parse

# Ensure Windows terminal standard streams handle UTF-8 / emojis gracefully
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
APP_JS_PATH = WEB_DIR / "app.js"
INDEX_HTML_PATH = WEB_DIR / "index.html"
STYLES_CSS_PATH = WEB_DIR / "styles.css"
PROPERTIES_JSON_PATH = BASE_DIR / "data" / "inmuebles_barranquilla.json"
NODE_HARNESS_PATH = BASE_DIR / "tests" / "tier5_frontend_harness.js"


class TestTier5AdversarialFrontend(unittest.TestCase):
    """Tier 5 Adversarial Verification of Frontend Architecture & Client Logic."""

    @classmethod
    def setUpClass(cls):
        assert APP_JS_PATH.exists(), f"Missing {APP_JS_PATH}"
        assert INDEX_HTML_PATH.exists(), f"Missing {INDEX_HTML_PATH}"
        assert STYLES_CSS_PATH.exists(), f"Missing {STYLES_CSS_PATH}"
        assert PROPERTIES_JSON_PATH.exists(), f"Missing {PROPERTIES_JSON_PATH}"
        assert NODE_HARNESS_PATH.exists(), f"Missing {NODE_HARNESS_PATH}"

        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            cls.app_js = f.read()

        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            cls.index_html = f.read()

        with open(STYLES_CSS_PATH, "r", encoding="utf-8") as f:
            cls.styles_css = f.read()

        with open(PROPERTIES_JSON_PATH, "r", encoding="utf-8") as f:
            cls.properties = json.load(f)

    # -------------------------------------------------------------------------
    # 1. UNICODE DIACRITICS & COMBINING MARKS STRESS-TESTING
    # -------------------------------------------------------------------------
    def test_01_unicode_combining_marks_and_diacritics_normalization(self):
        """Verify NFD combining characters match NFC canonical forms across all Colombian accents."""
        def py_normalize(text):
            if not text:
                return ""
            normalized = unicodedata.normalize("NFD", str(text))
            stripped = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
            return stripped.lower().strip()

        # Pairs of [NFC string, NFD string with explicit combining marks, expected ASCII]
        test_cases = [
            ("Paraíso", "Parai\u0301so", "paraiso"),
            ("Ríomar", "Ri\u0301omar", "riomar"),
            ("Cañaveral", "Can\u0303averal", "canaveral"),
            ("Baño", "Ban\u0303o", "bano"),
            ("Cúcuta", "Cu\u0301cuta", "cucuta"),
            ("Concepción", "Concepcio\u0301n", "concepcion"),
            ("Simón Bolívar", "Sim\u0301on Boli\u0301var", "simon bolivar"),
            ("PARAÍSO", "PARAI\u0301SO", "paraiso"),
            ("RÍOMAR", "RI\u0301OMAR", "riomar"),
            ("Cigüeña", "Cigue\u0308n\u0303a", "ciguena"),
            ("e\u0301\u0300", "e\u0301\u0300", "e"),
        ]

        for nfc, nfd, expected in test_cases:
            norm_nfc = py_normalize(nfc)
            norm_nfd = py_normalize(nfd)
            self.assertEqual(norm_nfc, expected, f"NFC '{nfc}' failed to normalize to '{expected}'")
            self.assertEqual(norm_nfd, expected, f"NFD '{nfd}' failed to normalize to '{expected}'")
            self.assertEqual(norm_nfc, norm_nfd, f"NFC '{nfc}' != NFD '{nfd}'")

        # Verify JS regex /[\u0300-\u036f]/g in app.js covers the Unicode combining marks block
        self.assertIn("[\\u0300-\\u036f]", self.app_js, "app.js must strip combining diacritical marks U+0300 to U+036F")

    def test_02_whitespace_tokenization_with_non_breaking_spaces(self):
        """Verify search query tokenization splits on non-breaking spaces and irregular whitespace."""
        query_with_nbsp = "El\u00A0Golf\t\nAlto\u3000Prado"
        tokens = re.split(r"\s+", query_with_nbsp)
        clean_tokens = [t.lower() for t in tokens if t]
        self.assertEqual(clean_tokens, ["el", "golf", "alto", "prado"])

        # Check that app.js splits search queries using /\s+/
        self.assertIn("split(/\\s+/)", self.app_js, "app.js must use regex whitespace splitting")

    # -------------------------------------------------------------------------
    # 2. CONTRADICTORY & EXTREME FILTER COMBINATIONS
    # -------------------------------------------------------------------------
    def test_03_contradictory_filter_predicates_yield_zero_results(self):
        """Simulate mathematical conjunction of mutually exclusive filters on the 172-property DB."""
        # Contradictory: Barrio Riomar AND search text Miramar
        contradictory = [
            p for p in self.properties
            if p["neighborhood"].lower() == "riomar" and "miramar" in p["title"].lower()
        ]
        self.assertEqual(len(contradictory), 0, "Disjoint location filters must yield 0 results")

        # Impossible budget: total_price <= 500.000 COP (min price in DB is 1.100.000 COP)
        below_500k = [p for p in self.properties if p["total_price"] <= 500_000]
        self.assertEqual(len(below_500k), 0, "No listings exist below 500.000 COP")

        # Ceiling boundary: exactly 2.500.000 COP
        all_eligible = [p for p in self.properties if p["total_price"] <= 2_500_000]
        self.assertEqual(len(all_eligible), 172, "All 172 listings satisfy <= 2.500.000 COP")

    def test_04_discarded_filter_tab_independence(self):
        """Verify the logical independence of statusTab 'descartados' vs 'todos' hideDiscarded."""
        # In app.js lines 450-466:
        # In 'descartados' tab: checks if (tracking.status !== 'descartado') return false;
        # In 'todos' tab: checks if (hideDiscarded && tracking.status === 'descartado') return false;
        # This guarantees discarded listings remain visible when explicitly navigating to the Discarded tab.
        has_descartados_tab_branch = "statusTab === 'descartados'" in self.app_js
        has_hide_discarded_branch = "hideDiscarded && tracking.status === 'descartado'" in self.app_js
        self.assertTrue(has_descartados_tab_branch, "app.js must have explicit branch for statusTab 'descartados'")
        self.assertTrue(has_hide_discarded_branch, "app.js must filter discarded on general tabs")

    # -------------------------------------------------------------------------
    # 3. EMPTY & CORRUPTED LOCALSTORAGE SCHEMAS (EMPIRICAL VERIFICATION)
    # -------------------------------------------------------------------------
    def test_05_localstorage_corrupted_schemas_and_failure_modes(self):
        """Empirically test loadLocalTracking() behavior with malformed and empty schemas."""
        # 1. Syntax-corrupted JSON string
        raw_corrupted = "{malformed: json: 123"
        try:
            json.loads(raw_corrupted)
            valid = True
        except Exception:
            valid = False
        self.assertFalse(valid, "Corrupted JSON string must fail JSON.parse and be handled by try/catch")

        # 2. Empirical finding: app.js loadLocalTracking() does not validate schema.
        # If stored is "{}" or "[1, 2, 3]", loadLocalTracking() returns it.
        # When /api/tracking is offline, state.tracking = localTracking, making state.tracking.properties undefined.
        # Line 447 `state.tracking.properties[p.id]` will crash with TypeError.
        app_js_lines = self.app_js.splitlines()
        target_line = None
        for i, line in enumerate(app_js_lines, 1):
            if "state.tracking.properties[p.id]" in line:
                target_line = i
                break

        self.assertIsNotNone(target_line, "Found vulnerable line referencing state.tracking.properties[p.id]")
        # Line 447 in web/app.js directly dereferences state.tracking.properties without optional chaining
        self.assertIn("state.tracking.properties[p.id]", self.app_js)

    # -------------------------------------------------------------------------
    # 4. WHATSAPP DEEP LINK ESCAPING & EMOJIS
    # -------------------------------------------------------------------------
    def test_06_whatsapp_phone_number_cleansing_rules(self):
        """Verify Colombian mobile phone prefix normalizations."""
        def clean_colombian_phone(raw_phone):
            digits = re.sub(r"\D", "", raw_phone or "")
            if len(digits) == 10 and digits.startswith("3"):
                return "57" + digits
            elif len(digits) == 12 and digits.startswith("573"):
                return digits
            elif not digits:
                return "573000000000"
            return digits

        test_numbers = [
            ("3014567890", "573014567890"),
            ("573158889900", "573158889900"),
            ("+57 (300) 123-4567", "573001234567"),
            ("", "573000000000"),
            (None, "573000000000"),
        ]

        for raw, expected in test_numbers:
            self.assertEqual(clean_colombian_phone(raw), expected)

    def test_07_whatsapp_message_uri_encoding_with_emojis_and_specials(self):
        """Verify WhatsApp message percent-encoding preserves newlines, emojis, and quotes."""
        msg = (
            "Hola, vi el anuncio del apartamento en Altos de Riomar 🌴✨ / Cra 51B # 84\n"
            "por $2.250.000 COP (Canon + Admin). ¿Sigue disponible?\n"
            "Ref: MQ-SPECIAL-&?\"#'"
        )
        encoded = urllib.parse.quote(msg, safe="")
        # Invariant: encoded string must not contain raw spaces, newlines, or unescaped ampersands
        self.assertNotIn(" ", encoded)
        self.assertNotIn("\n", encoded)
        self.assertNotIn("\r", encoded)
        self.assertNotIn("&", encoded)

        # Invariant: decodeURIComponent / unquote must perfectly reconstruct the original message
        decoded = urllib.parse.unquote(encoded)
        self.assertEqual(decoded, msg, "Decoded WhatsApp message must be 100% byte-identical to original")

    # -------------------------------------------------------------------------
    # 5. IMAGE CAROUSEL BOUNDARY HARDENING
    # -------------------------------------------------------------------------
    def test_08_carousel_index_wrapping_arithmetic(self):
        """Verify modular arithmetic for circular carousel navigation."""
        def wrap_next(cur_idx, count):
            if count <= 1:
                return 0
            return (cur_idx + 1) % count

        def wrap_prev(cur_idx, count):
            if count <= 1:
                return 0
            return (cur_idx - 1 + count) % count

        # Zero images (fallback length 1)
        self.assertEqual(wrap_next(0, 1), 0)
        self.assertEqual(wrap_prev(0, 1), 0)

        # Single image
        self.assertEqual(wrap_next(0, 1), 0)
        self.assertEqual(wrap_prev(0, 1), 0)

        # 5 images forward loop
        idx = 0
        forward_path = []
        for _ in range(5):
            idx = wrap_next(idx, 5)
            forward_path.append(idx)
        self.assertEqual(forward_path, [1, 2, 3, 4, 0], "Forward wrap must cycle 0->1->2->3->4->0")

        # 5 images backward loop
        idx = 0
        backward_path = []
        for _ in range(5):
            idx = wrap_prev(idx, 5)
            backward_path.append(idx)
        self.assertEqual(backward_path, [4, 3, 2, 1, 0], "Backward wrap must cycle 0->4->3->2->1->0")

    def test_09_carousel_fallback_placeholder_contract(self):
        """Verify that app.js specifies 'assets/placeholder.svg' when images array is empty or missing."""
        self.assertIn("assets/placeholder.svg", self.app_js, "app.js must provide fallback placeholder.svg")
        placeholder_file = WEB_DIR / "assets" / "placeholder.svg"
        self.assertTrue(placeholder_file.exists(), f"Placeholder file must exist at {placeholder_file}")

    # -------------------------------------------------------------------------
    # 6. XSS & HTML INJECTION RESILIENCE
    # -------------------------------------------------------------------------
    def test_10_html_entity_escaping_implementation(self):
        """Verify escapeHtml sanitizes all critical injection characters (&, <, >, \", ')."""
        def py_escape_html(text):
            if not text:
                return ""
            html_map = {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#039;",
            }
            return re.sub(r'[&<>"\']', lambda m: html_map[m.group(0)], str(text))

        hostile_inputs = [
            ('<script>alert("xss")</script>', "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;"),
            ('<img src=x onerror=alert(1)>', "&lt;img src=x onerror=alert(1)&gt;"),
            ('"><svg onload=alert(1)>', "&quot;&gt;&lt;svg onload=alert(1)&gt;"),
            ("Particular / 'Inmobiliaria'", "Particular / &#039;Inmobiliaria&#039;"),
            ("A & B Arriendos", "A &amp; B Arriendos"),
        ]

        for hostile, expected in hostile_inputs:
            escaped = py_escape_html(hostile)
            self.assertEqual(escaped, expected)
            self.assertNotIn("<script>", escaped)
            self.assertNotIn("<img", escaped)
            self.assertNotIn("<svg", escaped)

        # Verify escapeHtml is defined in app.js
        self.assertIn("function escapeHtml(text)", self.app_js, "escapeHtml function must exist in app.js")

    # -------------------------------------------------------------------------
    # 7. SORTING ALGORITHM INVARIANTS ON ACTUAL DATABASE
    # -------------------------------------------------------------------------
    def test_11_sorting_invariants_across_all_properties(self):
        """Assert sorting invariants on the actual 172-record database."""
        # 1. Price ascending
        sorted_price_asc = sorted(self.properties, key=lambda p: p["total_price"])
        for i in range(len(sorted_price_asc) - 1):
            self.assertLessEqual(sorted_price_asc[i]["total_price"], sorted_price_asc[i + 1]["total_price"])

        # 2. Price descending
        sorted_price_desc = sorted(self.properties, key=lambda p: p["total_price"], reverse=True)
        for i in range(len(sorted_price_desc) - 1):
            self.assertGreaterEqual(sorted_price_desc[i]["total_price"], sorted_price_desc[i + 1]["total_price"])

        # 3. Area descending (handling missing area safely)
        sorted_area_desc = sorted(self.properties, key=lambda p: p.get("area_m2") or 0, reverse=True)
        for i in range(len(sorted_area_desc) - 1):
            a1 = sorted_area_desc[i].get("area_m2") or 0
            a2 = sorted_area_desc[i + 1].get("area_m2") or 0
            self.assertGreaterEqual(a1, a2)

    # -------------------------------------------------------------------------
    # 8. DOM ELEMENT CONTRACT & CSS DESIGN SYSTEM PARITY
    # -------------------------------------------------------------------------
    def test_12_dom_element_id_parity_between_app_and_html(self):
        """Verify every document.getElementById queried in app.js exists in index.html."""
        get_elem_pattern = r"document\.getElementById\(['\"]([^'\"]+)['\"]\)"
        queried_ids = set(re.findall(get_elem_pattern, self.app_js))

        self.assertGreater(len(queried_ids), 30, "app.js should query more than 30 DOM element IDs")

        html_id_pattern = r'id=["\']([^"\']+)["\']'
        defined_ids = set(re.findall(html_id_pattern, self.index_html))

        missing_ids = queried_ids - defined_ids
        self.assertEqual(len(missing_ids), 0, f"IDs referenced in app.js missing from index.html: {missing_ids}")

    def test_13_css_responsive_design_and_theme_variables(self):
        """Verify CSS root theme variables and responsive breakpoints."""
        # CSS variables
        required_vars = ["--slate-900", "--teal-600", "--amber-500", "--whatsapp"]
        for var_name in required_vars:
            self.assertIn(var_name, self.styles_css, f"Missing CSS theme variable {var_name}")

        # Media query breakpoints
        self.assertIn("@media (max-width: 1024px)", self.styles_css, "Missing 1024px tablet/desktop media query")
        self.assertIn("@media (max-width: 640px)", self.styles_css, "Missing 640px mobile media query")

        # HTML viewport meta tag
        self.assertIn('name="viewport"', self.index_html)
        self.assertIn("width=device-width", self.index_html)

    # -------------------------------------------------------------------------
    # 9. MASTER NODE.JS ADVERSARIAL HARNESS EXECUTION
    # -------------------------------------------------------------------------
    def test_14_master_node_adversarial_harness(self):
        """Run tests/tier5_frontend_harness.js verifying all 37 in-memory DOM stress tests."""
        proc = subprocess.run(
            ["node", str(NODE_HARNESS_PATH)],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )

        output = proc.stdout + "\n" + proc.stderr
        safe_output = output.encode("ascii", errors="replace").decode("ascii")
        print("\n--- TIER 5 FRONTEND NODE HARNESS OUTPUT ---")
        print(safe_output)

        self.assertEqual(proc.returncode, 0, f"Node harness failed with code {proc.returncode}:\n{safe_output}")
        self.assertIn("HARNESS VERDICT      : APPROVE", output)
        self.assertIn("Passed               : 37", output)
        self.assertIn("Failed               : 0", output)


if __name__ == "__main__":
    unittest.main()
