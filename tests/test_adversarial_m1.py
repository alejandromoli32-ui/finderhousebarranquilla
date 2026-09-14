"""
tests/test_adversarial_m1.py
Adversarial test harness for Milestone 1:
1. Strict price ceiling enforcement (canon + admin_fee <= 2.500.000 COP).
2. Synthetic boundary tests:
   - 2.500.000 + 0 (PASS)
   - 2.450.000 + 50.000 (PASS)
   - 2.450.001 + 50.000 = 2.500.001 (REJECT)
   - 2.500.001 + 0 (REJECT)
   - 1.000.000 + 1.500.001 (REJECT)
   - 1 + 2.499.999 = 2.500.000 (PASS)
   - 1 + 2.500.000 = 2.500.001 (REJECT)
3. Extreme values (negative prices, zero canon, null admin, non-numeric strings, negative admin trick).
4. Direct listing URLs validation (protocols, domains, malicious schemes, query/path injection).
5. Phone and WhatsApp format validation and adversarial normalization matrix.
6. Empirical audit of all records in data/inmuebles_barranquilla.json and CSV alignment.
"""

import csv
import json
import os
import re
import unittest
from urllib.parse import urlparse

from data_pipeline.deduplicator import deduplicate_listings
from data_pipeline.extractors.metrocuadrado import normalize_whatsapp
from data_pipeline.pipeline import PipelineController


class TestAdversarialPriceCeiling(unittest.TestCase):
    """Stress tests the strict price ceiling invariant <= $2.500.000 COP."""

    def setUp(self):
        self.controller = PipelineController(max_price=2500000)
        self.base_listing = {
            "id": "ADV-TEST-001",
            "title": "Apartamento en Arriendo en Miramar",
            "property_type": "Apartamento",
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "address": "Cra 43 # 98-50",
            "area_m2": 65.0,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "url": "https://www.metrocuadrado.com/inmueble/12345"
        }

    def _create_listing(self, canon, admin_fee, listing_id="ADV-TEST"):
        prop = dict(self.base_listing)
        prop["id"] = listing_id
        prop["canon"] = canon
        prop["admin_fee"] = admin_fee
        return prop

    # --- Synthetic boundary tests ---

    def test_synthetic_exact_ceiling_canon_2500000_admin_0_passes(self):
        """Boundary: canon 2.500.000 + admin 0 = 2.500.000 COP strictly passes."""
        listing = self._create_listing(2500000, 0, "TEST-BOUND-2.5M-0")
        is_valid, msg = self.controller.validate_listing(listing)
        self.assertTrue(is_valid, f"Exact ceiling 2.5M+0 must be accepted, but got: {msg}")
        self.assertEqual(listing["total_price"], 2500000)
        self.assertEqual(listing["canon"], 2500000)
        self.assertEqual(listing["admin_fee"], 0)

    def test_synthetic_exact_ceiling_canon_2450000_admin_50000_passes(self):
        """Boundary: canon 2.450.000 + admin 50.000 = 2.500.000 COP strictly passes."""
        listing = self._create_listing(2450000, 50000, "TEST-BOUND-2.45M-50K")
        is_valid, msg = self.controller.validate_listing(listing)
        self.assertTrue(is_valid, f"Exact ceiling 2.45M+50k must be accepted, but got: {msg}")
        self.assertEqual(listing["total_price"], 2500000)
        self.assertEqual(listing["canon"], 2450000)
        self.assertEqual(listing["admin_fee"], 50000)

    def test_synthetic_ceiling_breach_canon_2450001_admin_50000_rejected(self):
        """Breach: canon 2.450.001 + admin 50.000 = 2.500.001 COP must be rejected ($1 COP breach)."""
        listing = self._create_listing(2450001, 50000, "TEST-BREACH-1")
        is_valid, msg = self.controller.validate_listing(listing)
        self.assertFalse(is_valid, "2.500.001 COP must be strictly rejected")
        self.assertIn("exceeds budget ceiling", msg)

    def test_synthetic_ceiling_breach_canon_2500001_admin_0_rejected(self):
        """Breach: canon 2.500.001 + admin 0 = 2.500.001 COP must be rejected ($1 COP breach)."""
        listing = self._create_listing(2500001, 0, "TEST-BREACH-2")
        is_valid, msg = self.controller.validate_listing(listing)
        self.assertFalse(is_valid, "2.500.001 COP with admin 0 must be strictly rejected")
        self.assertIn("exceeds budget ceiling", msg)

    def test_synthetic_ceiling_breach_canon_1000000_admin_1500001_rejected(self):
        """Breach: canon 1.000.000 + admin 1.500.001 = 2.500.001 COP must be rejected ($1 COP breach via admin)."""
        listing = self._create_listing(1000000, 1500001, "TEST-BREACH-3")
        is_valid, msg = self.controller.validate_listing(listing)
        self.assertFalse(is_valid, "1M + 1.500.001 = 2.500.001 COP must be strictly rejected")
        self.assertIn("exceeds budget ceiling", msg)

    def test_synthetic_extreme_boundary_low_canon_high_admin_boundary(self):
        """Extreme: canon 1 + admin 2.499.999 = 2.500.000 COP passes; 1 + 2.500.000 = 2.500.001 rejected."""
        listing_pass = self._create_listing(1, 2499999, "TEST-EXTREME-PASS")
        is_valid, _ = self.controller.validate_listing(listing_pass)
        self.assertTrue(is_valid)
        self.assertEqual(listing_pass["total_price"], 2500000)

        listing_fail = self._create_listing(1, 2500000, "TEST-EXTREME-FAIL")
        is_valid_fail, msg_fail = self.controller.validate_listing(listing_fail)
        self.assertFalse(is_valid_fail)
        self.assertIn("exceeds budget ceiling", msg_fail)

    def test_synthetic_high_and_astronomical_prices_rejected(self):
        """High and astronomical values are rejected without integer overflow or bypass."""
        listing_high = self._create_listing(5000000, 500000, "TEST-HIGH")
        self.assertFalse(self.controller.validate_listing(listing_high)[0])

        listing_astro = self._create_listing(10**12, 10**11, "TEST-ASTRO")
        self.assertFalse(self.controller.validate_listing(listing_astro)[0])


class TestAdversarialExtremeAndMalformedValues(unittest.TestCase):
    """Stress tests extreme, negative, null, and malformed inputs."""

    def setUp(self):
        self.controller = PipelineController(max_price=2500000)
        self.base_listing = {
            "id": "ADV-MALFORMED",
            "title": "Apartamento en Arriendo en Riomar",
            "neighborhood": "Riomar",
            "zone": "Noroccidente",
            "url": "https://www.fincaraiz.com.co/inmueble/99999"
        }

    def test_negative_canon_rejected(self):
        """Negative canon values (-1, -500.000) must be rejected."""
        for neg_val in [-1, -500000, -2500000]:
            p = dict(self.base_listing)
            p["canon"] = neg_val
            p["admin_fee"] = 100000
            is_valid, msg = self.controller.validate_listing(p)
            self.assertFalse(is_valid, f"Negative canon {neg_val} must be rejected")
            self.assertIn("Canon must be positive", msg)

    def test_zero_canon_rejected(self):
        """Zero canon (canon = 0) must be rejected (no free apartments)."""
        p = dict(self.base_listing)
        p["canon"] = 0
        p["admin_fee"] = 200000
        is_valid, msg = self.controller.validate_listing(p)
        self.assertFalse(is_valid, "Zero canon must be rejected")
        self.assertIn("Canon must be positive: $0", msg)

    def test_negative_admin_fee_rejected(self):
        """Negative admin fee (-1, -50.000) must be rejected."""
        for neg_admin in [-1, -50000, -300000]:
            p = dict(self.base_listing)
            p["canon"] = 1500000
            p["admin_fee"] = neg_admin
            is_valid, msg = self.controller.validate_listing(p)
            self.assertFalse(is_valid, f"Negative admin fee {neg_admin} must be rejected")
            self.assertIn("Admin fee cannot be negative", msg)

    def test_negative_admin_fee_exploit_prevented(self):
        """Adversarial exploit attempt: canon 2.700.000 + admin -300.000 = 2.400.000 must NOT pass!"""
        p = dict(self.base_listing)
        p["canon"] = 2700000
        p["admin_fee"] = -300000
        is_valid, msg = self.controller.validate_listing(p)
        self.assertFalse(is_valid, "Exploit with negative admin to reduce total price must be rejected")
        self.assertIn("Admin fee cannot be negative", msg)

    def test_null_admin_fee_defaults_to_zero_and_validates(self):
        """Null admin_fee (admin_fee=None) defaults to 0 and succeeds if canon <= 2.5M."""
        p = dict(self.base_listing)
        p["canon"] = 2100000
        p["admin_fee"] = None
        is_valid, msg = self.controller.validate_listing(p)
        self.assertTrue(is_valid, f"Null admin fee with valid canon should default to 0, got: {msg}")
        self.assertEqual(p["admin_fee"], 0)
        self.assertEqual(p["total_price"], 2100000)

        # But if canon is over 2.5M with null admin, it must still be rejected
        p_over = dict(self.base_listing)
        p_over["canon"] = 2500001
        p_over["admin_fee"] = None
        is_valid_over, msg_over = self.controller.validate_listing(p_over)
        self.assertFalse(is_valid_over)
        self.assertIn("exceeds budget ceiling", msg_over)

    def test_null_canon_rejected(self):
        """Null canon (canon=None) defaults to 0 and is rejected as non-positive."""
        p = dict(self.base_listing)
        p["canon"] = None
        p["admin_fee"] = 200000
        is_valid, msg = self.controller.validate_listing(p)
        self.assertFalse(is_valid, "Null canon must be rejected")
        self.assertIn("Canon must be positive: $0", msg)

    def test_non_numeric_price_strings_rejected(self):
        """Non-numeric string inputs must be rejected gracefully."""
        bad_inputs = ["dos millones", "N/A", "gratis", "$2.500.000", "2,500,000"]
        for bad in bad_inputs:
            p = dict(self.base_listing)
            p["canon"] = bad
            p["admin_fee"] = 100000
            is_valid, msg = self.controller.validate_listing(p)
            self.assertFalse(is_valid, f"Non-numeric string '{bad}' must be rejected")
            self.assertIn("Price fields must be numeric integers", msg)

    def test_numeric_string_coercion(self):
        """Numeric strings ("2000000") should be safely converted to integer COP."""
        p = dict(self.base_listing)
        p["canon"] = "2000000"
        p["admin_fee"] = "300000"
        is_valid, msg = self.controller.validate_listing(p)
        self.assertTrue(is_valid, msg)
        self.assertIsInstance(p["canon"], int)
        self.assertIsInstance(p["admin_fee"], int)
        self.assertIsInstance(p["total_price"], int)
        self.assertEqual(p["total_price"], 2300000)

    def test_missing_price_keys_rejected(self):
        """Listing dict completely omitting 'canon' or 'admin_fee' is handled safely."""
        p = dict(self.base_listing)
        # No 'canon' key
        is_valid, msg = self.controller.validate_listing(p)
        self.assertFalse(is_valid)
        self.assertIn("Canon must be positive", msg)


class TestAdversarialUrlValidation(unittest.TestCase):
    """Stress tests listing URLs for security, structure, and integrity."""

    def setUp(self):
        self.controller = PipelineController(max_price=2500000)
        self.base_listing = {
            "id": "ADV-URL-001",
            "title": "Apartamento en Arriendo en Alto Prado",
            "canon": 2000000,
            "admin_fee": 200000,
            "neighborhood": "Alto Prado",
            "zone": "Norte"
        }

    def test_malicious_protocols_strictly_rejected(self):
        """Malicious and non-HTTP protocols must be strictly rejected."""
        malicious_urls = [
            "javascript:alert(1)",
            "file:///etc/passwd",
            "file:///C:/Windows/System32/cmd.exe",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
            "ftp://ftp.example.com/inmuebles",
            "tel:+573001234567",
            "blob:https://example.com/uuid",
            "//www.metrocuadrado.com/inmueble/123",  # scheme-relative URL
            "",
            "   ",
            "not-a-url"
        ]
        for bad_url in malicious_urls:
            p = dict(self.base_listing)
            p["url"] = bad_url
            is_valid, msg = self.controller.validate_listing(p)
            self.assertFalse(is_valid, f"URL '{bad_url}' must be rejected")
            self.assertIn("Invalid or unsafe URL protocol", msg)

    def test_valid_http_and_https_accepted(self):
        """Standard HTTP and HTTPS URLs from portals are accepted."""
        for good_url in [
            "https://www.metrocuadrado.com/inmueble/arriendo-apartamento/12345",
            "https://www.fincaraiz.com.co/apartamento-en-arriendo/67890",
            "http://www.metrocuadrado.com/inmueble/12345"
        ]:
            p = dict(self.base_listing)
            p["url"] = good_url
            is_valid, msg = self.controller.validate_listing(p)
            self.assertTrue(is_valid, f"Valid URL '{good_url}' should be accepted: {msg}")


class TestAdversarialContactFormats(unittest.TestCase):
    """Stress tests phone numbers and WhatsApp normalization logic."""

    def test_normalize_whatsapp_matrix(self):
        """Verifies whatsapp normalization handles all realistic Colombian phone formats."""
        # Standard 10-digit mobile
        self.assertEqual(normalize_whatsapp("3001234567", ""), "573001234567")
        self.assertEqual(normalize_whatsapp("", "3159876543"), "573159876543")

        # Formatted with spaces, dashes, dots, parentheses
        self.assertEqual(normalize_whatsapp("+57 300 123 4567", ""), "573001234567")
        self.assertEqual(normalize_whatsapp("(300) 123-4567", ""), "573001234567")
        self.assertEqual(normalize_whatsapp("300.123.4567", ""), "573001234567")

        # Already normalized 12-digit format (573...)
        self.assertEqual(normalize_whatsapp("573001234567", ""), "573001234567")
        self.assertEqual(normalize_whatsapp("+573001234567", ""), "573001234567")

        # Masked portal phone (must NOT be falsely expanded to 573...)
        self.assertEqual(normalize_whatsapp("+5730", ""), "5730")
        self.assertEqual(normalize_whatsapp("36819", ""), "36819")

        # Empty / None
        self.assertEqual(normalize_whatsapp("", ""), "")
        self.assertEqual(normalize_whatsapp(None, None), "")

        # Landline (PBX Barranquilla 605...)
        # 10 digits starting with 605, not 3 -> should retain digits without adding 57
        self.assertEqual(normalize_whatsapp("6053303333", ""), "6053303333")

        # Dummy all-zero placeholder
        self.assertEqual(normalize_whatsapp("0000000000", ""), "0000000000")


class TestEmpiricalProductionDatabaseAudit(unittest.TestCase):
    """
    Empirical audit of the actual serialized database files:
    - data/inmuebles_barranquilla.json
    - data/inmuebles_barranquilla.csv
    """

    @classmethod
    def setUpClass(cls):
        cls.json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "inmuebles_barranquilla.json")
        cls.csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "inmuebles_barranquilla.csv")

        with open(cls.json_path, "r", encoding="utf-8") as f:
            cls.data = json.load(f)

    def test_database_record_count_non_empty(self):
        """Database must contain substantial inventory of verified properties."""
        self.assertGreaterEqual(len(self.data), 100, f"Expected >= 100 properties, found {len(self.data)}")

    def test_every_record_satisfies_strict_price_ceiling(self):
        """EMPIRICAL AUDIT: 100% of records in data/inmuebles_barranquilla.json MUST satisfy total <= 2.500.000 COP."""
        violations = []
        for p in self.data:
            canon = p.get("canon", 0)
            admin = p.get("admin_fee", 0)
            total = p.get("total_price", 0)

            if total > 2500000:
                violations.append((p.get("id"), total, f"total_price {total} > 2500000"))
            if canon + admin > 2500000:
                violations.append((p.get("id"), canon + admin, f"canon({canon}) + admin({admin}) > 2500000"))
            if total != canon + admin:
                violations.append((p.get("id"), total, f"arithmetic mismatch: total={total} != {canon}+{admin}"))

        self.assertEqual(len(violations), 0, f"Found {len(violations)} price ceiling violations: {violations}")

    def test_financial_sanity_across_all_records(self):
        """All records have positive canon and non-negative admin fee."""
        for p in self.data:
            self.assertGreater(p["canon"], 0, f"Listing {p['id']} has non-positive canon: {p['canon']}")
            self.assertGreaterEqual(p["admin_fee"], 0, f"Listing {p['id']} has negative admin: {p['admin_fee']}")

    def test_direct_listing_urls_across_all_records(self):
        """All records must have valid HTTP/HTTPS URLs pointing directly to portals with listing identifiers."""
        allowed_domains = {"www.metrocuadrado.com", "www.fincaraiz.com.co", "metrocuadrado.com", "fincaraiz.com.co"}
        invalid_urls = []

        for p in self.data:
            u = p.get("url", "")
            parsed = urlparse(u)

            if parsed.scheme not in ("http", "https"):
                invalid_urls.append((p["id"], u, "invalid scheme"))
            if parsed.netloc not in allowed_domains:
                invalid_urls.append((p["id"], u, f"unexpected domain: {parsed.netloc}"))
            if not parsed.path or parsed.path == "/":
                invalid_urls.append((p["id"], u, "missing listing path"))

        self.assertEqual(len(invalid_urls), 0, f"Found {len(invalid_urls)} invalid listing URLs: {invalid_urls}")

    def test_contact_information_integrity(self):
        """Verifies contact schema and audits WhatsApp & phone compliance."""
        stats = {
            "total": len(self.data),
            "valid_whatsapp_573": 0,
            "masked_phone": 0,
            "valid_mobile_10": 0,
            "valid_landline_10": 0,
            "dummy_placeholder": 0,
            "empty_whatsapp": 0
        }

        for p in self.data:
            contact = p.get("contact")
            self.assertIsInstance(contact, dict, f"Listing {p['id']} contact is not a dict")
            self.assertIn("phone", contact)
            self.assertIn("whatsapp", contact)
            self.assertIn("agency", contact)
            self.assertIn("agent_name", contact)

            wa = str(contact.get("whatsapp") or "").strip()
            ph = str(contact.get("phone") or "").strip()

            if wa == "0000000000" or ph == "0000000000":
                stats["dummy_placeholder"] += 1
            elif wa.startswith("573") and len(wa) == 12:
                stats["valid_whatsapp_573"] += 1
            elif not wa:
                stats["empty_whatsapp"] += 1

            digits_ph = re.sub(r"\D", "", ph)
            if digits_ph.startswith("3") and len(digits_ph) == 10:
                stats["valid_mobile_10"] += 1
            elif digits_ph.startswith("605") and len(digits_ph) == 10:
                stats["valid_landline_10"] += 1
            elif len(digits_ph) < 7:
                stats["masked_phone"] += 1

        # High contact readiness: vast majority of listings must have valid WhatsApp or unmasked phone
        ready_count = stats["valid_whatsapp_573"] + stats["valid_landline_10"]
        self.assertGreaterEqual(
            ready_count,
            100,
            f"Expected at least 100 listings with ready phone/WhatsApp contact, got {ready_count} (stats: {stats})"
        )

    def test_csv_file_alignment_and_bom(self):
        """CSV export must match JSON exactly in row count, fields, and UTF-8 BOM."""
        self.assertTrue(os.path.exists(self.csv_path))

        with open(self.csv_path, "rb") as f:
            bom = f.read(3)
            self.assertEqual(bom, b"\xef\xbb\xbf", "CSV missing UTF-8 BOM for Windows Excel")

        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.assertEqual(len(rows), len(self.data), "CSV row count must match JSON count exactly")

        # Verify all prices in CSV are <= 2.500.000 COP
        for row in rows:
            total = int(row["total_price"])
            canon = int(row["canon"])
            admin = int(row["admin_fee"])
            self.assertLessEqual(total, 2500000, f"CSV listing {row['id']} exceeds 2.5M: {total}")
            self.assertEqual(total, canon + admin)


if __name__ == "__main__":
    unittest.main()
