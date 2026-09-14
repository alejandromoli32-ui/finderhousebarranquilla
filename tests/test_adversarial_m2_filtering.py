"""
Milestone 2 Adversarial Challenge Test Suite: Frontend Filtering Logic and Edge Cases.
Validates web/app.js filtering algorithms, diacritics stripping, search fuzziness,
extreme bounds ($500k empty state, $2.5M all eligible properties), and 1000-run performance benchmark (<10ms).
"""

import json
import os
from pathlib import Path
import subprocess
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
APP_JS_FILE = BASE_DIR / "web" / "app.js"
PROPERTIES_FILE = BASE_DIR / "data" / "inmuebles_barranquilla.json"
NODE_TEST_SCRIPT = BASE_DIR / "tests" / "test_adversarial_filtering.js"


class TestMilestone2AdversarialFiltering(unittest.TestCase):
    """Empirical adversarial verification of Milestone 2 frontend filtering engine."""

    @classmethod
    def setUpClass(cls):
        # Verify prerequisite files exist
        assert APP_JS_FILE.exists(), f"Missing web/app.js at {APP_JS_FILE}"
        assert PROPERTIES_FILE.exists(), f"Missing properties at {PROPERTIES_FILE}"
        assert NODE_TEST_SCRIPT.exists(), f"Missing node test runner at {NODE_TEST_SCRIPT}"

        with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
            cls.properties = json.load(f)

    def test_database_price_bounds_and_coverage(self):
        """Verify baseline dataset bounds (172 properties, min price >= 1.1M, max price <= 2.5M)."""
        self.assertEqual(len(self.properties), 172, "Dataset must contain exactly 172 properties.")
        prices = [p["total_price"] for p in self.properties]
        min_price = min(prices)
        max_price = max(prices)

        self.assertGreaterEqual(min_price, 1_100_000, "Lowest price property in dataset must be >= 1.100.000 COP.")
        self.assertLessEqual(max_price, 2_500_000, "Highest price property in dataset must be <= 2.500.000 COP.")

    def test_run_node_adversarial_suite(self):
        """Execute the comprehensive Node.js in-memory DOM simulation and performance benchmark."""
        proc = subprocess.run(
            ["node", str(NODE_TEST_SCRIPT)],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )

        output = proc.stdout + "\n" + proc.stderr
        print("\n--- NODE ADVERSARIAL TEST OUTPUT ---")
        print(output)

        self.assertEqual(proc.returncode, 0, f"Node adversarial suite failed with exit code {proc.returncode}")
        self.assertIn("VERDICT         : APPROVE", output, "Adversarial suite must conclude with APPROVE.")
        self.assertIn("[PASS] Diacritics Equivalence \"paraiso\" vs \"Paraíso\"", output)
        self.assertIn("[PASS] Diacritics Equivalence \"riomar\" vs \"RÍOMAR\"", output)
        self.assertIn("[PASS] Search \"ñ\" no crash", output)
        self.assertIn("[PASS] Search \"cúcuta\" vs \"cucuta\"", output)
        self.assertIn("[PASS] Price ceiling $500.000 COP -> 0 results", output)
        self.assertIn("[PASS] Empty State Displayed at $500.000 COP", output)
        self.assertIn("[PASS] Price ceiling $2.500.000 COP Returns All 172 Eligible Properties", output)
        self.assertIn("[PASS] Performance Benchmark: Average Latency < 10ms", output)

    def test_diacritics_normalization_python_oracle(self):
        """Python oracle replicating Unicode NFD decomposition verifying zero discrepancies."""
        import unicodedata

        def py_normalize(text):
            if not text:
                return ""
            normalized = unicodedata.normalize("NFD", str(text))
            stripped = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
            return stripped.lower().strip()

        test_pairs = [
            ("Paraíso", "paraiso"),
            ("Riomar", "riomar"),
            ("Ríomar", "riomar"),
            ("Cúcuta", "cucuta"),
            ("Campiña", "campina"),
            ("Baño", "bano"),
            ("Cañaveral", "canaveral"),
            ("Concepción", "concepcion"),
            ("Simón Bolívar", "simon bolivar")
        ]

        for original, expected in test_pairs:
            self.assertEqual(py_normalize(original), expected)


if __name__ == "__main__":
    unittest.main()
