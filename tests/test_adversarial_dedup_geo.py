"""
tests/test_adversarial_dedup_geo.py
Empirical Adversarial Test Suite for:
1. Deduplication Engine (Synthetic duplicates clustering/merging & Non-duplicates isolation)
2. Geographic Integrity of data/inmuebles_barranquilla.json (Sector bounds & leak detection)
3. Schema & Physical Invariants Audit (Bedrooms, Stratum, Zone interface contracts)
4. Exact 1:1 JSON vs CSV match verification
"""

import csv
import json
import os
import re
import unittest
from collections import Counter
from typing import Any, Dict, List

from data_pipeline.deduplicator import (
    calculate_similarity,
    compute_canonical_key,
    deduplicate_listings,
    merge_cluster,
    normalize_neighborhood,
)
from data_pipeline.pipeline import ALLOWED_BARRIOS, PipelineController

JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "inmuebles_barranquilla.json")
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "inmuebles_barranquilla.csv")


class TestAdversarialDeduplicationSyntheticDuplicates(unittest.TestCase):
    """Adversarially tests synthetic duplicate detection, clustering, and attribute merging."""

    def test_fuzzy_price_delta_50k_and_area_delta_1m2_merged(self):
        """Listing pair with $50.000 COP price difference and 1 m2 area difference must merge."""
        prop_a = {
            "id": "SYN-A1",
            "portal": "Metrocuadrado",
            "title": "Apartamento en Arriendo en Miramar",
            "property_type": "Apartamento",
            "canon": 2000000,
            "admin_fee": 150000,
            "total_price": 2150000,
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "address": "Cra 43 # 98-50",
            "area_m2": 65.0,
            "bedrooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "images": ["https://images.com/a1.jpg"],
            "url": "https://metro.com/a1",
            "contact": {"phone": "3007771690", "whatsapp": "573007771690", "agency": "Agencia Metro", "agent_name": "Juan"},
            "description": "Excelente apto",
            "verified": True
        }
        prop_b = {
            "id": "SYN-B1",
            "portal": "Finca Raiz",
            "title": "Arriendo Miramar 3 Alcobas",
            "property_type": "Apartamento",
            "canon": 2100000,
            "admin_fee": 0,
            "total_price": 2100000,  # $50.000 cheaper
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "address": "Cra 43 # 98-50",
            "area_m2": 66.0,  # 1 m2 difference
            "bedrooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "images": ["https://images.com/b1.jpg"],
            "url": "https://fincaraiz.com/b1",
            "contact": {"phone": "+5730", "whatsapp": "", "agency": "Agencia Finca", "agent_name": ""},
            "description": "Gran oportunidad",
            "verified": False
        }

        sim = calculate_similarity(prop_a, prop_b)
        self.assertGreaterEqual(sim, 0.70, f"Similarity should be >= 0.70, got {sim}")

        deduped, stats = deduplicate_listings([prop_a, prop_b])
        self.assertEqual(len(deduped), 1, "Duplicate listings must be merged into 1 record")
        self.assertEqual(stats["merged_duplicates"], 1)

        merged = deduped[0]
        self.assertEqual(merged["total_price"], 2100000)
        self.assertEqual(merged["admin_fee"], 150000)
        self.assertEqual(merged["canon"], 1950000)
        self.assertEqual(merged["contact"]["phone"], "3007771690")
        self.assertEqual(merged["contact"]["whatsapp"], "573007771690")
        self.assertEqual(len(merged["images"]), 2)
        self.assertIn("https://images.com/a1.jpg", merged["images"])
        self.assertIn("https://images.com/b1.jpg", merged["images"])

    def test_fuzzy_price_delta_100k_and_area_delta_3m2_merged(self):
        """Listing pair with $100.000 COP delta and 3 m2 delta with street match merges."""
        prop_a = {
            "id": "SYN-A2",
            "portal": "Metrocuadrado",
            "title": "Apartamento en Riomar",
            "property_type": "Apartamento",
            "canon": 2400000,
            "admin_fee": 0,
            "total_price": 2400000,
            "neighborhood": "Riomar",
            "zone": "Norte",
            "address": "Cra 51 # 96-30",
            "area_m2": 75.0,
            "bedrooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 5,
            "url": "https://metro.com/a2",
            "contact": {"phone": "3101234567", "whatsapp": "573101234567", "agency": "Riomar Real Estate"}
        }
        prop_b = {
            "id": "SYN-B2",
            "portal": "Finca Raiz",
            "title": "Apartamento en Riomar",
            "property_type": "Apartamento",
            "canon": 2100000,
            "admin_fee": 400000,
            "total_price": 2500000,  # delta = $100.000
            "neighborhood": "Altos de Riomar",  # Synonym
            "zone": "Norte",
            "address": "Cra 51 # 96-30",
            "area_m2": 72.0,  # delta = 3.0 m2
            "bedrooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 5,
            "url": "https://fincaraiz.com/b2",
            "contact": {"phone": "+5731", "whatsapp": "", "agency": "Inmobiliaria Norte"}
        }
        sim = calculate_similarity(prop_a, prop_b)
        self.assertGreaterEqual(sim, 0.70, f"Expected similarity >= 0.70, got {sim}")

        deduped, stats = deduplicate_listings([prop_a, prop_b])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["total_price"], 2400000)
        self.assertEqual(deduped[0]["admin_fee"], 400000)
        self.assertEqual(deduped[0]["canon"], 2000000)

    def test_transitive_clustering_union_find(self):
        """Three listings A, B, C where A clusters with B, and B clusters with C must collapse into 1 record."""
        prop_a = {
            "id": "TRANS-A", "portal": "Metrocuadrado", "neighborhood": "Miramar",
            "total_price": 2000000, "canon": 2000000, "admin_fee": 0,
            "bedrooms": 2, "bathrooms": 2, "area_m2": 60.0, "url": "https://p.com/a",
            "address": "Cra 43 # 99"
        }
        prop_b = {
            "id": "TRANS-B", "portal": "Finca Raiz", "neighborhood": "Miramar",
            "total_price": 2050000, "canon": 1850000, "admin_fee": 200000,
            "bedrooms": 2, "bathrooms": 2, "area_m2": 61.0, "url": "https://p.com/b",
            "address": "Cra 43 # 99"
        }
        prop_c = {
            "id": "TRANS-C", "portal": "Ciencuadras", "neighborhood": "Miramar",
            "total_price": 2100000, "canon": 2100000, "admin_fee": 0,
            "bedrooms": 2, "bathrooms": 2, "area_m2": 62.0, "url": "https://p.com/c",
            "address": "Cra 43 # 99"
        }

        deduped, stats = deduplicate_listings([prop_a, prop_b, prop_c])
        self.assertEqual(len(deduped), 1, "Transitive duplicates A-B-C must form a single merged cluster")
        self.assertEqual(stats["merged_duplicates"], 2)
        self.assertEqual(deduped[0]["total_price"], 2000000)
        self.assertEqual(deduped[0]["admin_fee"], 200000)
        self.assertEqual(deduped[0]["canon"], 1800000)


class TestAdversarialDeduplicationNonDuplicates(unittest.TestCase):
    """Adversarially tests that non-duplicate properties are strictly isolated and never falsely merged."""

    def test_different_bedrooms_in_same_building_never_merge(self):
        """2-bedroom vs 3-bedroom in same building and same price must never merge."""
        prop_a = {
            "id": "ISO-BED2", "portal": "Metrocuadrado", "neighborhood": "Miramar",
            "title": "Apartamento Conjunto Sorrento 2 Hab", "address": "Conjunto Sorrento",
            "total_price": 2200000, "canon": 2200000, "admin_fee": 0,
            "bedrooms": 2, "bathrooms": 2, "area_m2": 60.0, "url": "https://p.com/1"
        }
        prop_b = {
            "id": "ISO-BED3", "portal": "Finca Raiz", "neighborhood": "Miramar",
            "title": "Apartamento Conjunto Sorrento 3 Hab", "address": "Conjunto Sorrento",
            "total_price": 2200000, "canon": 2200000, "admin_fee": 0,
            "bedrooms": 3, "bathrooms": 2, "area_m2": 60.0, "url": "https://p.com/2"
        }

        sim = calculate_similarity(prop_a, prop_b)
        self.assertEqual(sim, 0.0, f"Hard gate should yield 0.0, got {sim}")
        deduped, stats = deduplicate_listings([prop_a, prop_b])
        self.assertEqual(len(deduped), 2, "Different bedroom counts must remain separate listings")
        self.assertEqual(stats["merged_duplicates"], 0)

    def test_price_delta_exceeding_150k_never_merge(self):
        """Apartments with price delta > $150.000 COP must never merge."""
        prop_a = {
            "id": "ISO-P1800", "portal": "Metrocuadrado", "neighborhood": "Miramar",
            "total_price": 1800000, "canon": 1800000, "admin_fee": 0,
            "bedrooms": 3, "bathrooms": 2, "area_m2": 68.0, "url": "https://p.com/1"
        }
        prop_b = {
            "id": "ISO-P2100", "portal": "Finca Raiz", "neighborhood": "Miramar",
            "total_price": 2100000, "canon": 2100000, "admin_fee": 0,
            "bedrooms": 3, "bathrooms": 2, "area_m2": 68.0, "url": "https://p.com/2"
        }

        sim = calculate_similarity(prop_a, prop_b)
        self.assertEqual(sim, 0.0)
        deduped, stats = deduplicate_listings([prop_a, prop_b])
        self.assertEqual(len(deduped), 2)
        self.assertEqual(stats["merged_duplicates"], 0)

    def test_price_delta_boundary_150001_rejected_150000_allowed(self):
        """Exact price boundary check: delta = $150.000 allowed, delta = $150.001 rejected."""
        base_a = {
            "id": "BASE-A", "portal": "Metrocuadrado", "neighborhood": "Miramar",
            "total_price": 2000000, "canon": 2000000, "admin_fee": 0,
            "bedrooms": 3, "bathrooms": 2, "area_m2": 65.0, "url": "https://p.com/a"
        }
        prop_150k = {
            "id": "PROP-150K", "portal": "Finca Raiz", "neighborhood": "Miramar",
            "total_price": 2150000, "canon": 2150000, "admin_fee": 0,
            "bedrooms": 3, "bathrooms": 2, "area_m2": 65.0, "url": "https://p.com/b"
        }
        prop_150k_plus1 = {
            "id": "PROP-150K-1", "portal": "Finca Raiz", "neighborhood": "Miramar",
            "total_price": 2150001, "canon": 2150001, "admin_fee": 0,
            "bedrooms": 3, "bathrooms": 2, "area_m2": 65.0, "url": "https://p.com/c"
        }

        sim_150k = calculate_similarity(base_a, prop_150k)
        sim_150k_plus1 = calculate_similarity(base_a, prop_150k_plus1)

        self.assertGreaterEqual(sim_150k, 0.70, "Delta of exactly 150.000 should be evaluated and score >= 0.70")
        self.assertEqual(sim_150k_plus1, 0.0, "Delta of 150.001 must be hard rejected with similarity 0.0")

    def test_different_bathrooms_difference_gte_2_never_merge(self):
        """Apartments with bathroom difference >= 2 must never merge."""
        prop_a = {
            "id": "ISO-BATH1", "portal": "Metrocuadrado", "neighborhood": "Miramar",
            "total_price": 2000000, "bedrooms": 3, "bathrooms": 1, "area_m2": 65.0, "url": "https://p.com/1"
        }
        prop_b = {
            "id": "ISO-BATH3", "portal": "Finca Raiz", "neighborhood": "Miramar",
            "total_price": 2000000, "bedrooms": 3, "bathrooms": 3, "area_m2": 65.0, "url": "https://p.com/2"
        }
        sim = calculate_similarity(prop_a, prop_b)
        self.assertEqual(sim, 0.0, "Bathroom difference of 2 must hard-reject similarity")
        deduped, _ = deduplicate_listings([prop_a, prop_b])
        self.assertEqual(len(deduped), 2)

    def test_conflicting_building_names_never_merge(self):
        """Apartments in explicitly different known buildings must never merge."""
        prop_a = {
            "id": "BLD-SORRENTO", "portal": "Metrocuadrado", "neighborhood": "Miramar",
            "title": "Apartamento Edificio Sorrento", "address": "Conjunto Sorrento",
            "total_price": 2200000, "bedrooms": 3, "bathrooms": 2, "area_m2": 68.0, "url": "https://p.com/1"
        }
        prop_b = {
            "id": "BLD-TORINO", "portal": "Finca Raiz", "neighborhood": "Miramar",
            "title": "Apartamento Edificio Torino", "address": "Conjunto Torino",
            "total_price": 2200000, "bedrooms": 3, "bathrooms": 2, "area_m2": 68.0, "url": "https://p.com/2"
        }
        sim = calculate_similarity(prop_a, prop_b)
        self.assertEqual(sim, 0.0, "Conflicting building names must hard-reject similarity")
        deduped, _ = deduplicate_listings([prop_a, prop_b])
        self.assertEqual(len(deduped), 2)

    def test_different_neighborhoods_never_merge(self):
        """Apartments in different neighborhoods must never merge."""
        prop_a = {
            "id": "GEO-MIRAMAR", "portal": "Metrocuadrado", "neighborhood": "Miramar",
            "total_price": 2200000, "bedrooms": 3, "bathrooms": 2, "area_m2": 68.0, "url": "https://p.com/1"
        }
        prop_b = {
            "id": "GEO-GOLF", "portal": "Finca Raiz", "neighborhood": "El Golf",
            "total_price": 2200000, "bedrooms": 3, "bathrooms": 2, "area_m2": 68.0, "url": "https://p.com/2"
        }
        sim = calculate_similarity(prop_a, prop_b)
        self.assertEqual(sim, 0.0)
        deduped, _ = deduplicate_listings([prop_a, prop_b])
        self.assertEqual(len(deduped), 2)

    def test_large_area_difference_without_token_never_merge(self):
        """Area difference > 5 m2 without matching building tokens must never merge."""
        prop_a = {
            "id": "AREA-50M2", "portal": "Metrocuadrado", "neighborhood": "Miramar",
            "total_price": 2000000, "bedrooms": 2, "bathrooms": 2, "area_m2": 50.0, "url": "https://p.com/1"
        }
        prop_b = {
            "id": "AREA-65M2", "portal": "Finca Raiz", "neighborhood": "Miramar",
            "total_price": 2000000, "bedrooms": 2, "bathrooms": 2, "area_m2": 65.0, "url": "https://p.com/2"
        }
        sim = calculate_similarity(prop_a, prop_b)
        self.assertEqual(sim, 0.0, "Area difference of 15 m2 without building token must hard-reject")
        deduped, _ = deduplicate_listings([prop_a, prop_b])
        self.assertEqual(len(deduped), 2)


class TestGeographicIntegrityEmpirical(unittest.TestCase):
    """Audits data/inmuebles_barranquilla.json for geographic integrity and leakage."""

    @classmethod
    def setUpClass(cls):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            cls.listings = json.load(f)

    def test_exact_record_count_is_172(self):
        """Database must contain exactly 172 records."""
        self.assertEqual(len(self.listings), 172)

    def test_price_ceiling_and_arithmetic_all_173_records(self):
        """All 173 records must strictly satisfy total_price <= 2.500.000 COP and canon + admin_fee == total_price."""
        for idx, p in enumerate(self.listings):
            total = p.get("total_price")
            canon = p.get("canon")
            admin = p.get("admin_fee")
            pid = p.get("id")

            self.assertIsNotNone(total, f"Missing total_price in listing {pid}")
            self.assertLessEqual(total, 2500000, f"Listing {pid} exceeds 2.5M COP: {total}")
            self.assertGreater(canon, 0, f"Listing {pid} canon must be > 0: {canon}")
            self.assertGreaterEqual(admin, 0, f"Listing {pid} admin_fee must be >= 0: {admin}")
            self.assertEqual(total, canon + admin, f"Listing {pid} price math mismatch: {total} != {canon} + {admin}")

    def test_southern_barranquilla_zero_leakage(self):
        """No listings should belong to southern/south-eastern sectors of Barranquilla."""
        southern_tokens = [
            r"\brebolo\b", r"\bchinita\b", r"\bla chinita\b", r"\bel bosque\b",
            r"\bsimon bolivar\b", r"\bsimón bolívar\b", r"\bsan roque\b",
            r"\bchiquinquira\b", r"\bchiquinquirá\b", r"\bmontes\b", r"\blos montes\b",
            r"\bsoledad\b", r"\bmalambo\b", r"\bgalapa\b", r"\bbaranoa\b",
            r"\bsabanagrande\b", r"\bsuroriente\b", r"\bsuroccidente\b"
        ]

        leaks = []
        for p in self.listings:
            text = f"{p.get('neighborhood', '')} {p.get('title', '')} {p.get('address', '')} {p.get('zone', '')}".lower()
            for pat in southern_tokens:
                if re.search(pat, text):
                    leaks.append((p.get("id"), p.get("neighborhood"), pat))

        self.assertEqual(len(leaks), 0, f"Found southern or external municipal leaks: {leaks}")

    def test_adversarial_leakage_audit_puerto_colombia(self):
        """
        Adversarial test: Ensures no non-Barranquilla municipality listing leaks in.
        Detects FR-191933365 (neighborhood='Puerto colombia').
        """
        puerto_colombia_listings = [
            p for p in self.listings
            if str(p.get("neighborhood", "")).strip().lower() == "puerto colombia"
            or "puerto-colombia" in str(p.get("url", "")).lower()
        ]
        # This test documents the leak if present
        leak_ids = [p.get("id") for p in puerto_colombia_listings]
        print(f"\n[LEAK DETECTION] Puerto Colombia municipality listings count: {len(leak_ids)} (IDs: {leak_ids})")
        # In a strict test, this must be 0
        self.assertEqual(
            len(puerto_colombia_listings), 0,
            f"Adversarial Failure: Non-Barranquilla municipality listings leaked: {leak_ids}"
        )

    def test_zone_interface_contract_conformance(self):
        """
        Adversarial test: Verifies PROJECT.md interface contract:
        'zone': string ('Norte' | 'Noroccidente').
        Detects MERGED-21392-M7032477-194143777 (zone='Otros').
        """
        invalid_zone_listings = [
            p for p in self.listings
            if p.get("zone") not in ["Norte", "Noroccidente"]
        ]
        invalid_ids = [(p.get("id"), p.get("zone")) for p in invalid_zone_listings]
        print(f"\n[SCHEMA AUDIT] Invalid zone listings count: {len(invalid_ids)}: {invalid_ids}")
        self.assertEqual(
            len(invalid_zone_listings), 0,
            f"Adversarial Failure: Listings violate zone contract: {invalid_ids}"
        )

    def test_bedrooms_valid_positive_count(self):
        """
        Adversarial test: Bedrooms must be a valid non-negative integer count (>= 0).
        Clamps sentinels such as -1 to 0 (studio apartments).
        """
        negative_bedroom_listings = [
            p for p in self.listings
            if p.get("bedrooms") is None or p.get("bedrooms") < 0
        ]
        bad_ids = [(p.get("id"), p.get("bedrooms")) for p in negative_bedroom_listings]
        print(f"\n[PHYSICAL AUDIT] Negative bedroom listings: {bad_ids}")
        self.assertEqual(
            len(negative_bedroom_listings), 0,
            f"Adversarial Failure: Invalid bedroom counts: {bad_ids}"
        )

    def test_stratum_in_socioeconomic_range_1_to_6(self):
        """
        Adversarial test: Verifies PROJECT.md interface contract:
        'stratum': number (int 1-6) or None.
        Out-of-range stratum is sanitized to None.
        """
        invalid_stratum_listings = [
            p for p in self.listings
            if p.get("stratum") is not None and p.get("stratum") not in range(1, 7)
        ]
        bad_ids = [(p.get("id"), p.get("stratum")) for p in invalid_stratum_listings]
        print(f"\n[PHYSICAL AUDIT] Out of range stratum listings: {bad_ids}")
        self.assertEqual(
            len(invalid_stratum_listings), 0,
            f"Adversarial Failure: Invalid stratum outside 1-6: {bad_ids}"
        )


class TestJsonVsCsvExactParity(unittest.TestCase):
    """Verifies that data/inmuebles_barranquilla.json and data/inmuebles_barranquilla.csv match 1:1."""

    @classmethod
    def setUpClass(cls):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            cls.json_data = json.load(f)

        with open(CSV_PATH, "rb") as f:
            bom = f.read(3)
            cls.has_bom = (bom == b'\xef\xbb\xbf')

        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cls.csv_data = list(reader)
            cls.csv_fieldnames = reader.fieldnames

    def test_csv_has_utf8_bom(self):
        """CSV file must begin with UTF-8 BOM for Microsoft Excel Windows compatibility."""
        self.assertTrue(self.has_bom, "CSV missing UTF-8 BOM (\\xef\\xbb\\xbf)")

    def test_exact_row_count_match(self):
        """CSV row count must match JSON record count (172 == 172)."""
        self.assertEqual(len(self.json_data), len(self.csv_data))
        self.assertEqual(len(self.json_data), 172)

    def test_exact_id_sequence_match(self):
        """The sequence of IDs in CSV must match JSON exactly."""
        for i in range(len(self.json_data)):
            j_id = self.json_data[i]["id"]
            c_id = self.csv_data[i]["id"]
            self.assertEqual(j_id, c_id, f"ID mismatch at index {i}: JSON '{j_id}' != CSV '{c_id}'")

    def test_field_by_field_parity(self):
        """All fields must have identical values between JSON and CSV."""
        for i in range(len(self.json_data)):
            j = self.json_data[i]
            c = self.csv_data[i]
            pid = j["id"]

            self.assertEqual(j["portal"], c["portal"], f"Portal mismatch for {pid}")
            self.assertEqual(j["title"], c["title"], f"Title mismatch for {pid}")
            self.assertEqual(j["property_type"], c["property_type"], f"Property type mismatch for {pid}")
            self.assertEqual(j["canon"], int(c["canon"]), f"Canon mismatch for {pid}")
            self.assertEqual(j["admin_fee"], int(c["admin_fee"]), f"Admin fee mismatch for {pid}")
            self.assertEqual(j["total_price"], int(c["total_price"]), f"Total price mismatch for {pid}")
            self.assertEqual(j["neighborhood"], c["neighborhood"], f"Neighborhood mismatch for {pid}")
            self.assertEqual(j["zone"], c["zone"], f"Zone mismatch for {pid}")
            self.assertEqual(j["address"], c["address"], f"Address mismatch for {pid}")
            self.assertAlmostEqual(float(j["area_m2"]), float(c["area_m2"]), places=2, msg=f"Area mismatch for {pid}")
            self.assertEqual(j["bedrooms"], int(c["bedrooms"]), f"Bedrooms mismatch for {pid}")
            self.assertEqual(j["bathrooms"], int(c["bathrooms"]), f"Bathrooms mismatch for {pid}")
            self.assertEqual(j["parking"], int(c["parking"]), f"Parking mismatch for {pid}")
            if j["stratum"] is None:
                self.assertEqual(c["stratum"], "", f"Stratum mismatch for {pid}")
            else:
                self.assertEqual(j["stratum"], int(c["stratum"]), f"Stratum mismatch for {pid}")
            self.assertEqual(j["url"], c["url"], f"URL mismatch for {pid}")

            # Contact
            contact = j.get("contact") or {}
            self.assertEqual(contact.get("phone", ""), c["contact_phone"], f"Phone mismatch for {pid}")
            self.assertEqual(contact.get("whatsapp", ""), c["contact_whatsapp"], f"WhatsApp mismatch for {pid}")
            self.assertEqual(contact.get("agency", ""), c["contact_agency"], f"Agency mismatch for {pid}")
            self.assertEqual(contact.get("agent_name", ""), c["contact_agent_name"], f"Agent name mismatch for {pid}")

            # Images
            images = j.get("images") or []
            self.assertEqual(len(images), int(c["images_count"]), f"Images count mismatch for {pid}")
            expected_main = images[0] if images else ""
            self.assertEqual(expected_main, c["main_image"], f"Main image mismatch for {pid}")

            # Price per m2 calculation parity
            area = float(j.get("area_m2") or 0.0)
            expected_pm2 = int(round(j["total_price"] / area)) if area > 0 else 0
            self.assertEqual(expected_pm2, int(c["price_per_m2"]), f"Price/m2 formula mismatch for {pid}")


if __name__ == "__main__":
    unittest.main()
