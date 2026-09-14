"""
tests/test_pipeline.py
Unit test suite verifying:
- Price ceiling exact boundary ($2.500.000 allowed, $2.500.001 rejected)
- Admin fee calculation ($0 admin when included or separate)
- Fuzzy deduplication between portals (exact and fuzzy matching, attribute merging)
- Schema completeness for all required fields in PROJECT.md
- JSON and CSV output validity with UTF-8 BOM
"""

import csv
import json
import os
import tempfile
import unittest

from data_pipeline.deduplicator import (
    calculate_similarity,
    compute_canonical_key,
    deduplicate_listings,
    merge_cluster,
    normalize_neighborhood,
)
from data_pipeline.extractors.fincaraiz import FincaRaizExtractor
from data_pipeline.extractors.metrocuadrado import MetrocuadradoExtractor, normalize_whatsapp
from data_pipeline.pipeline import PipelineController


class TestPriceCeilingAndValidation(unittest.TestCase):
    """Verifies strict price ceiling enforcement and listing validation."""

    def setUp(self):
        self.controller = PipelineController(max_price=2500000)

    def test_price_ceiling_exact_boundary_accepted(self):
        """$2.500.000 COP total is strictly allowed (inclusive boundary)."""
        prop = {
            "id": "BOUNDARY-2500000",
            "title": "Apartamento en Arriendo en Miramar",
            "canon": 2100000,
            "admin_fee": 400000,
            "total_price": 2500000,
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "url": "https://example.com/miramar-1"
        }
        is_valid, msg = self.controller.validate_listing(prop)
        self.assertTrue(is_valid, f"Listing with exactly $2.5M should be accepted, got: {msg}")
        self.assertEqual(prop["total_price"], 2500000)

    def test_price_ceiling_breach_rejected_2500001(self):
        """$2.500.001 COP total is strictly rejected ($1 COP over budget)."""
        prop = {
            "id": "BREACH-2500001",
            "title": "Apartamento en Arriendo en Miramar",
            "canon": 2100000,
            "admin_fee": 400001,
            "total_price": 2500001,
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "url": "https://example.com/miramar-2"
        }
        is_valid, msg = self.controller.validate_listing(prop)
        self.assertFalse(is_valid, "Listing exceeding $2.5M by 1 COP must be rejected")
        self.assertIn("exceeds budget ceiling", msg)

    def test_price_ceiling_high_value_rejected_3500000(self):
        """High-value properties (> $2.5M) are strictly rejected."""
        prop = {
            "id": "HIGH-3500000",
            "title": "Penthouse en El Golf",
            "canon": 3000000,
            "admin_fee": 500000,
            "total_price": 3500000,
            "neighborhood": "El Golf",
            "zone": "Norte",
            "url": "https://example.com/golf-penthouse"
        }
        is_valid, msg = self.controller.validate_listing(prop)
        self.assertFalse(is_valid, "Listing with $3.5M must be rejected")
        self.assertIn("exceeds budget ceiling", msg)

    def test_admin_fee_zero_when_included_accepted(self):
        """Listing with admin included in canon ($0 admin fee) is valid."""
        prop = {
            "id": "ADMIN-INCLUDED",
            "title": "Apartamento Villa Carolina con admin incluida",
            "canon": 2350000,
            "admin_fee": 0,
            "total_price": 2350000,
            "neighborhood": "Villa Carolina",
            "zone": "Norte",
            "url": "https://example.com/carolina-1"
        }
        is_valid, msg = self.controller.validate_listing(prop)
        self.assertTrue(is_valid, f"Listing with $0 admin fee should be accepted, got: {msg}")
        self.assertEqual(prop["admin_fee"], 0)
        self.assertEqual(prop["total_price"], 2350000)

    def test_admin_fee_separate_calculation_accepted(self):
        """Listing with separate canon and admin fee is correctly validated."""
        prop = {
            "id": "ADMIN-SEPARATE",
            "title": "Apartamento Riomar",
            "canon": 1900000,
            "admin_fee": 350000,
            "total_price": 2250000,
            "neighborhood": "Riomar",
            "zone": "Noroccidente",
            "url": "https://example.com/riomar-1"
        }
        is_valid, msg = self.controller.validate_listing(prop)
        self.assertTrue(is_valid, msg)
        self.assertEqual(prop["total_price"], 2250000)

    def test_negative_or_zero_canon_rejected(self):
        """Listing with zero or negative canon is invalid."""
        prop_zero = {
            "id": "ZERO-CANON", "title": "Apto", "canon": 0, "admin_fee": 200000,
            "neighborhood": "Miramar", "url": "https://example.com"
        }
        prop_neg = {
            "id": "NEG-CANON", "title": "Apto", "canon": -500000, "admin_fee": 200000,
            "neighborhood": "Miramar", "url": "https://example.com"
        }
        self.assertFalse(self.controller.validate_listing(prop_zero)[0])
        self.assertFalse(self.controller.validate_listing(prop_neg)[0])

    def test_negative_admin_fee_rejected(self):
        """Listing with negative admin fee is invalid."""
        prop_neg_admin = {
            "id": "NEG-ADMIN", "title": "Apto", "canon": 1500000, "admin_fee": -50000,
            "neighborhood": "Miramar", "url": "https://example.com"
        }
        self.assertFalse(self.controller.validate_listing(prop_neg_admin)[0])

    def test_missing_required_fields_rejected(self):
        """Missing id or title leads to rejection."""
        no_id = {"title": "Apto Miramar", "canon": 1500000, "admin_fee": 0, "url": "https://x.com"}
        no_title = {"id": "ID-1", "canon": 1500000, "admin_fee": 0, "url": "https://x.com"}
        self.assertFalse(self.controller.validate_listing(no_id)[0])
        self.assertFalse(self.controller.validate_listing(no_title)[0])

    def test_insecure_or_malformed_url_rejected(self):
        """URLs with non-http/https schemes are rejected."""
        bad_url = {
            "id": "URL-1", "title": "Apto", "canon": 1500000, "admin_fee": 0,
            "neighborhood": "Miramar", "zone": "Norte", "url": "javascript:alert(1)"
        }
        is_valid, msg = self.controller.validate_listing(bad_url)
        self.assertFalse(is_valid)
        self.assertIn("Invalid or unsafe URL", msg)

    def test_geography_boundary_enforcement(self):
        """Listings outside Barranquilla Norte / Noroccidente are rejected."""
        south_prop = {
            "id": "SOUTH-1",
            "title": "Apartamento en Soledad",
            "canon": 1000000,
            "admin_fee": 100000,
            "total_price": 1100000,
            "neighborhood": "Soledad 2000",
            "zone": "Sur",
            "url": "https://example.com/soledad"
        }
        is_valid, msg = self.controller.validate_listing(south_prop)
        self.assertFalse(is_valid)
        self.assertIn("outside Barranquilla Norte", msg)


class TestDeduplicationEngine(unittest.TestCase):
    """Verifies fuzzy cross-portal deduplication and attribute merging."""

    def test_normalize_neighborhood_diacritics_and_casing(self):
        """Verifies neighborhood normalization removes accents, casing, and noise."""
        self.assertEqual(normalize_neighborhood("MIRAMAR Noroccidente"), "miramar")
        self.assertEqual(normalize_neighborhood("ALTO DE RIOMAR"), "riomar")
        self.assertEqual(normalize_neighborhood("Altos del Prado"), "alto_prado")
        self.assertEqual(normalize_neighborhood("Villa Carolina, Barranquilla"), "villa_carolina")
        self.assertEqual(normalize_neighborhood("El Golf"), "el_golf")
        self.assertEqual(normalize_neighborhood("Ciudad Mallorquín"), "ciudad_mallorquin")
        self.assertEqual(normalize_neighborhood(""), "desconocido")

    def test_compute_canonical_key_generation(self):
        """Canonical key discretizes continuous area and price into buckets."""
        prop = {
            "neighborhood": "Miramar",
            "bedrooms": 3,
            "bathrooms": 2,
            "area_m2": 68.4,
            "total_price": 2380000
        }
        key = compute_canonical_key(prop)
        self.assertEqual(key, "miramar_3hab_2ban_70m2_2400000cop")

    def test_exact_duplicate_detection(self):
        """Identical property listed on Metrocuadrado and Finca Raíz is detected and merged."""
        prop_mq = {
            "id": "MQ-1001",
            "portal": "Metrocuadrado",
            "title": "Apartamento en Arriendo en Miramar",
            "property_type": "Apartamento",
            "canon": 1800000,
            "admin_fee": 200000,
            "total_price": 2000000,
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "address": "Cra 43 # 98-50",
            "area_m2": 58.0,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "images": ["https://img.metro.com/1.jpg"],
            "url": "https://metro.com/1001",
            "contact": {"phone": "3007771690", "whatsapp": "573007771690", "agency": "Inmobiliaria Metro"}
        }
        prop_fr = {
            "id": "FR-2002",
            "portal": "Finca Raiz",
            "title": "Apartamento en Miramar",
            "property_type": "Apartamento",
            "canon": 1800000,
            "admin_fee": 200000,
            "total_price": 2000000,
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "address": "Cra 43 # 98-50",
            "area_m2": 58.0,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "images": ["https://img.finca.com/2.jpg"],
            "url": "https://fincaraiz.com/2002",
            "contact": {"phone": "+5730", "whatsapp": "", "agency": "Agencia Finca"}
        }
        sim = calculate_similarity(prop_mq, prop_fr)
        self.assertGreaterEqual(sim, 0.70, f"Similarity should be >= 0.70, got {sim}")

        deduped, stats = deduplicate_listings([prop_mq, prop_fr])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(stats["merged_duplicates"], 1)
        self.assertEqual(deduped[0]["portal"], "Metrocuadrado + Finca Raiz")
        self.assertIn("1001", deduped[0]["id"])
        self.assertIn("2002", deduped[0]["id"])

    def test_fuzzy_duplicate_sorrento_price_tolerance(self):
        """Empirical Sorrento case: $2.380.000 vs $2.300.000 (delta $80k COP) detected and merged."""
        prop_metro = {
            "id": "MQ-MC7032147",
            "portal": "Metrocuadrado",
            "title": "Apartamento en Arriendo, MIRAMAR Sorrento",
            "property_type": "Apartamento",
            "canon": 2380000,
            "admin_fee": 0,
            "total_price": 2380000,
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "address": "cr. sorrento",
            "area_m2": 68.4,
            "bedrooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "images": ["https://multimedia.metro.com/sorrento.jpg"],
            "url": "https://metro.com/sorrento",
            "contact": {"phone": "3174009707", "whatsapp": "573174009707", "agency": "Metro Broker"}
        }
        prop_finca = {
            "id": "FR-194130272",
            "portal": "Finca Raiz",
            "title": "Apartamento en arriendo en Miramar - Sorrento",
            "property_type": "Apartamento",
            "canon": 2000000,
            "admin_fee": 300000,
            "total_price": 2300000,
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "address": "Cra 43 # 98-50, Sorrento",
            "area_m2": 68.0,
            "bedrooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "images": ["https://cdn.finca.com/sorrento_hd.jpg"],
            "url": "https://finca.com/sorrento",
            "contact": {"phone": "+5730", "whatsapp": "", "agency": "BIENCO SAS"}
        }
        sim = calculate_similarity(prop_metro, prop_finca)
        self.assertGreaterEqual(sim, 0.70, f"Sorrento similarity should be >= 0.70, got {sim}")

        deduped, stats = deduplicate_listings([prop_metro, prop_finca])
        self.assertEqual(len(deduped), 1)
        # Optimal price should be the lower price ($2.300.000)
        self.assertEqual(deduped[0]["total_price"], 2300000)
        # Explicit admin fee from Finca Raiz should be preserved ($300.000)
        self.assertEqual(deduped[0]["admin_fee"], 300000)
        # Canon should be total - admin ($2.000.000)
        self.assertEqual(deduped[0]["canon"], 2000000)
        # Unmasked phone from Metrocuadrado should be preserved
        self.assertEqual(deduped[0]["contact"]["phone"], "3174009707")
        self.assertEqual(deduped[0]["contact"]["whatsapp"], "573174009707")
        # Photos should be combined (2 unique URLs)
        self.assertEqual(len(deduped[0]["images"]), 2)

    def test_distinct_properties_different_bedrooms_never_merged(self):
        """2-bedroom and 3-bedroom apartments in same building/price are never merged."""
        prop_a = {
            "id": "MQ-2BED", "portal": "Metrocuadrado", "neighborhood": "Miramar",
            "total_price": 2000000, "bedrooms": 2, "bathrooms": 2, "area_m2": 60.0
        }
        prop_b = {
            "id": "FR-3BED", "portal": "Finca Raiz", "neighborhood": "Miramar",
            "total_price": 2000000, "bedrooms": 3, "bathrooms": 2, "area_m2": 60.0
        }
        sim = calculate_similarity(prop_a, prop_b)
        self.assertEqual(sim, 0.0)
        deduped, stats = deduplicate_listings([prop_a, prop_b])
        self.assertEqual(len(deduped), 2)
        self.assertEqual(stats["merged_duplicates"], 0)

    def test_distinct_properties_different_barrios_never_merged(self):
        """Listings in different neighborhoods are never merged."""
        prop_a = {
            "id": "MQ-MIRAMAR", "portal": "Metrocuadrado", "neighborhood": "Miramar",
            "total_price": 2000000, "bedrooms": 2, "bathrooms": 2, "area_m2": 60.0
        }
        prop_b = {
            "id": "FR-PRADO", "portal": "Finca Raiz", "neighborhood": "Alto Prado",
            "total_price": 2000000, "bedrooms": 2, "bathrooms": 2, "area_m2": 60.0
        }
        sim = calculate_similarity(prop_a, prop_b)
        self.assertEqual(sim, 0.0)
        deduped, _ = deduplicate_listings([prop_a, prop_b])
        self.assertEqual(len(deduped), 2)

    def test_distinct_properties_different_buildings_never_merged(self):
        """Listings in explicitly different buildings are never merged."""
        prop_a = {
            "id": "MQ-TORINO", "portal": "Metrocuadrado", "neighborhood": "Miramar",
            "title": "Apartamento Edificio Torino", "address": "Edificio Torino",
            "total_price": 2200000, "bedrooms": 3, "bathrooms": 2, "area_m2": 70.0
        }
        prop_b = {
            "id": "FR-SORRENTO", "portal": "Finca Raiz", "neighborhood": "Miramar",
            "title": "Apartamento Conjunto Sorrento", "address": "Conjunto Sorrento",
            "total_price": 2200000, "bedrooms": 3, "bathrooms": 2, "area_m2": 70.0
        }
        sim = calculate_similarity(prop_a, prop_b)
        self.assertEqual(sim, 0.0)
        deduped, _ = deduplicate_listings([prop_a, prop_b])
        self.assertEqual(len(deduped), 2)

    def test_attribute_merging_combines_galleries_and_contact(self):
        """Merged listing retains unmasked phone/WhatsApp and combines image URLs."""
        prop_a = {
            "id": "MQ-1", "portal": "Metrocuadrado", "title": "Apto Miramar",
            "total_price": 2000000, "canon": 2000000, "admin_fee": 0,
            "neighborhood": "Miramar", "bedrooms": 2, "bathrooms": 2, "area_m2": 55.0,
            "url": "https://metro.com/1",
            "contact": {"phone": "3001234567", "whatsapp": "573001234567", "agency": "Agencia A"},
            "images": ["https://img.com/1.jpg", "https://img.com/2.jpg?track=1"]
        }
        prop_b = {
            "id": "FR-1", "portal": "Finca Raiz", "title": "Apto Miramar",
            "total_price": 2000000, "canon": 2000000, "admin_fee": 0,
            "neighborhood": "Miramar", "bedrooms": 2, "bathrooms": 2, "area_m2": 55.0,
            "url": "https://finca.com/1",
            "contact": {"phone": "+5730", "whatsapp": "", "agency": "Agencia B"},
            "images": ["https://img.com/2.jpg?track=2", "https://img.com/3.jpg"]
        }
        merged = merge_cluster([prop_a, prop_b])
        # Phone & WhatsApp from Metrocuadrado
        self.assertEqual(merged["contact"]["phone"], "3001234567")
        self.assertEqual(merged["contact"]["whatsapp"], "573001234567")
        # Combined agencies
        self.assertIn("Agencia A", merged["contact"]["agency"])
        self.assertIn("Agencia B", merged["contact"]["agency"])
        # Combined images: 1.jpg, 2.jpg (deduped query params), 3.jpg -> 3 images
        self.assertEqual(len(merged["images"]), 3)
        # Provenance tracking
        self.assertEqual(len(merged["source_urls"]), 2)
        self.assertEqual(len(merged["source_ids"]), 2)


class TestExtractors(unittest.TestCase):
    """Verifies individual extractor normalization methods."""

    def test_metrocuadrado_normalization(self):
        """Metrocuadrado raw item maps to canonical schema with unmasked WhatsApp."""
        ext = MetrocuadradoExtractor()
        raw_item = {
            "midinmueble": "9999",
            "title": "Apartamento en Arriendo en Miramar",
            "mvalorarriendo": 1800000,
            "data": {"mvaloradministracion": 200000, "mnombrevisitor": "Broker SAS"},
            "mnombrecomunbarrio": "Miramar",
            "marea": 65.0,
            "mnrocuartos": 3,
            "mnrobanos": 2,
            "mnrogarajes": 1,
            "estrato": 4,
            "link": "/inmueble/9999",
            "contactPhone": "3001234567",
            "whatsapp": "3001234567",
            "imageLink": "https://multimedia.metro.com/9999_p.jpg"
        }
        mapped = ext.normalize_property(raw_item, "Miramar", "Noroccidente")
        self.assertIsNotNone(mapped)
        self.assertEqual(mapped["id"], "MQ-9999")
        self.assertEqual(mapped["canon"], 1800000)
        self.assertEqual(mapped["admin_fee"], 200000)
        self.assertEqual(mapped["total_price"], 2000000)
        self.assertEqual(mapped["contact"]["whatsapp"], "573001234567")
        self.assertTrue(mapped["images"][0].endswith(".jpg"))
        self.assertFalse(mapped["images"][0].endswith("_p.jpg"))

    def test_fincaraiz_normalization(self):
        """Finca Raíz raw item maps to canonical schema with correct admin fee breakdown."""
        ext = FincaRaizExtractor()
        raw_item = {
            "id": 8888,
            "title": "Apartamento en Villa Carolina",
            "price": {"amount": 1700000, "admin_included": 2000000},
            "commonExpenses": {"amount": 300000},
            "locations": {"location_main": {"name": "Villa Carolina"}},
            "m2": 72.0,
            "bedrooms": 3,
            "bathrooms": 2,
            "garage": 1,
            "stratum": 4,
            "link": "/apartamento/8888",
            "owner": {"name": "Inmobiliaria Finca", "masked_phone": "+5730"},
            "description": "Excelente apto contactar al 3158889900"
        }
        mapped = ext.normalize_property(raw_item, "Villa Carolina", "Norte")
        self.assertIsNotNone(mapped)
        self.assertEqual(mapped["id"], "FR-8888")
        self.assertEqual(mapped["total_price"], 2000000)
        self.assertEqual(mapped["canon"], 1700000)
        self.assertEqual(mapped["admin_fee"], 300000)
        self.assertEqual(mapped["contact"]["phone"], "3158889900")
        self.assertEqual(mapped["contact"]["whatsapp"], "573158889900")


class TestSerializationAndIntegration(unittest.TestCase):
    """Verifies output files, schema completeness, and CSV BOM integrity."""

    def test_schema_completeness_and_json_csv_export(self):
        """Verifies all required fields exist, JSON is valid, and CSV has UTF-8 BOM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, "inmuebles.json")
            csv_file = os.path.join(tmpdir, "inmuebles.csv")

            controller = PipelineController(
                max_price=2500000,
                offline=True,
                output_json=json_file,
                output_csv=csv_file
            )
            metrics = controller.run()

            self.assertGreater(metrics["final_count"], 0)
            self.assertTrue(os.path.exists(json_file))
            self.assertTrue(os.path.exists(csv_file))

            # 1. Inspect JSON
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertIsInstance(data, list)
            self.assertEqual(len(data), metrics["final_count"])

            required_fields = [
                "id", "portal", "title", "property_type", "canon", "admin_fee",
                "total_price", "neighborhood", "zone", "address", "area_m2",
                "bedrooms", "bathrooms", "parking", "stratum", "images", "url",
                "contact", "description", "verified"
            ]

            for idx, prop in enumerate(data):
                for field in required_fields:
                    self.assertIn(field, prop, f"Property at index {idx} ({prop.get('id')}) missing field '{field}'")

                # Invariant checks
                self.assertLessEqual(prop["total_price"], 2500000)
                self.assertEqual(prop["total_price"], prop["canon"] + prop["admin_fee"])
                self.assertGreater(prop["canon"], 0)
                self.assertGreaterEqual(prop["admin_fee"], 0)
                self.assertIsInstance(prop["contact"], dict)
                self.assertIn("phone", prop["contact"])
                self.assertIn("whatsapp", prop["contact"])
                self.assertIsInstance(prop["images"], list)
                self.assertTrue(prop["url"].startswith("http"))

            # 2. Inspect CSV
            with open(csv_file, "rb") as f:
                raw_bom = f.read(3)
                self.assertEqual(
                    raw_bom,
                    b'\xef\xbb\xbf',
                    "CSV must begin with UTF-8 BOM (\\xef\\xbb\\xbf) for Microsoft Excel on Windows compatibility"
                )

            with open(csv_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            self.assertEqual(len(rows), len(data), "CSV row count must match JSON array length exactly")
            self.assertIn("total_price", reader.fieldnames)
            self.assertIn("contact_whatsapp", reader.fieldnames)


if __name__ == "__main__":
    unittest.main()
