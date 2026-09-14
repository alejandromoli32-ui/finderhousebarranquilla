#!/usr/bin/env python3
"""
tests/test_tier5_adversarial_backend.py
Tier 5 White-Box Adversarial Coverage Hardening for Python Backend & Data Pipelines.
Authored by challenger_final_1 for Final Milestone Phase 2.

Covers:
1. Pipeline Controller & Fallback Data Hardening (corrupt fallback datasets, unknown portals,
   whitelist conjuctions, Mallorquín border exemption, URL protocol gates, numeric sanitization).
2. Deduplication Engine Hardening (transitivity clustering in Union-Find, similarity hard gates,
   conflicting known buildings, bonus scoring matrix, cluster attribute merging matrix).
3. Local Dashboard Server Hardening (HTTP HEAD and OPTIONS methods, port auto-allocation limits,
   port 0 ephemeral binding, _TrackingFileProxy dunder protocols, disk corruption recovery,
   REST API error payloads and Content-Length fuzzing, static traversal barriers).
4. Curated Dossier & MFVI Mathematical Hardening (zero-price guards, division-by-zero protection,
   area boundaries, contact and amenity scoring, selection funnel quotas and backfills).
5. Metrocuadrado & Finca Raíz Extractor Hardening (RSC streams, Next.js hydration payloads,
   financial breakdown heuristics, cache fallback resilience).
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

# Ensure workspace root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from data_pipeline.deduplicator import (
    calculate_similarity,
    clean_id_prefix,
    compute_canonical_key,
    deduplicate_listings,
    merge_cluster,
    normalize_neighborhood,
)
from data_pipeline.extractors.fincaraiz import FincaRaizExtractor
from data_pipeline.extractors.metrocuadrado import (
    MetrocuadradoExtractor,
    clean_neighborhood_name,
    normalize_whatsapp,
)
from data_pipeline.pipeline import (
    ALLOWED_BARRIOS,
    BARRIO_TO_ZONE,
    DISALLOWED_MUNICIPALITIES,
    DISALLOWED_TOKENS,
    PipelineController,
)
from dossier_generator import (
    MultiFactorValueIndex,
    build_curator_thesis,
    build_inspection_checklist,
    clean_phone,
    format_cop,
    generate_dossier_markdown,
    generate_whatsapp_url,
    select_curated_properties,
)
from run_dashboard import (
    TRACKING_FILE,
    DashboardRequestHandler,
    ReusableThreadingServer,
    create_server,
    find_free_port,
    get_default_tracking,
    get_tracking_file_path,
    load_tracking_data,
    set_tracking_file_path,
    update_tracking_state,
)


class TestPipelineControllerAdversarial(unittest.TestCase):
    """Adversarial stress-testing of data ingestion, validation, and serialization."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.controller = PipelineController(
            max_price=2500000,
            output_json=str(self.tmp_path / "out.json"),
            output_csv=str(self.tmp_path / "out.csv"),
        )
        self.valid_base = {
            "id": "PIPE-001",
            "title": "Apartamento en Riomar",
            "property_type": "Apartamento",
            "canon": 2000000,
            "admin_fee": 300000,
            "total_price": 2300000,
            "neighborhood": "Riomar",
            "zone": "Noroccidente",
            "address": "Calle 90 # 58-30",
            "area_m2": 75.0,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "url": "https://www.metrocuadrado.com/inmueble/PIPE-001",
            "contact": {"phone": "3001234567", "whatsapp": "573001234567"},
            "images": ["https://img.com/1.jpg"],
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_fallback_dataset_nonexistent_path(self):
        """PipelineController gracefully returns [] when fallback file does not exist."""
        self.controller.fallback_path = str(self.tmp_path / "nonexistent_fallback.json")
        res = self.controller.load_fallback_dataset()
        self.assertEqual(res, [])

    def test_load_fallback_dataset_corrupted_json(self):
        """PipelineController catches JSONDecodeError and returns [] on corrupt fallback data."""
        bad_json = self.tmp_path / "corrupt.json"
        bad_json.write_text("{'unclosed_key': invalid json", encoding="utf-8")
        self.controller.fallback_path = str(bad_json)
        res = self.controller.load_fallback_dataset()
        self.assertEqual(res, [])

    def test_load_fallback_dataset_binary_garbage(self):
        """PipelineController catches decode errors on raw binary garbage and returns []."""
        bin_file = self.tmp_path / "binary.json"
        bin_file.write_bytes(b"\x00\xff\xfe\xca\xfe\xba\xbe")
        self.controller.fallback_path = str(bin_file)
        res = self.controller.load_fallback_dataset()
        self.assertEqual(res, [])

    def test_fetch_raw_listings_unknown_portal_triggers_fallback(self):
        """Specifying an unknown portal name causes safe fallback to local dataset."""
        fallback_file = self.tmp_path / "mock_fallback.json"
        mock_data = [{"id": "FB-1", "title": "Fallback", "canon": 1000000, "admin_fee": 0}]
        fallback_file.write_text(json.dumps(mock_data), encoding="utf-8")
        self.controller.fallback_path = str(fallback_file)
        self.controller.portals = "portal_inexistente"

        items = self.controller.fetch_raw_listings()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "FB-1")

    def test_fetch_raw_listings_offline_mode_reads_strictly_from_fallback(self):
        """Offline mode ignores live extractors and loads fallback dataset."""
        fallback_file = self.tmp_path / "mock_fallback.json"
        mock_data = [{"id": "OFF-1", "title": "Offline Prop"}]
        fallback_file.write_text(json.dumps(mock_data), encoding="utf-8")
        self.controller.fallback_path = str(fallback_file)
        self.controller.offline = True

        items = self.controller.fetch_raw_listings()
        self.assertEqual(items, mock_data)

    def test_validate_listing_non_dictionary_payloads(self):
        """Non-dictionary inputs return False with specific reason."""
        for invalid in ["string", 12345, [1, 2, 3], None, True]:
            ok, reason = self.controller.validate_listing(invalid)
            self.assertFalse(ok)
            self.assertEqual(reason, "Record is not a dictionary")

    def test_validate_listing_missing_id_and_title(self):
        """Missing ID or Title fails validation."""
        ok, reason = self.controller.validate_listing({"title": "Apto"})
        self.assertFalse(ok)
        self.assertIn("Missing listing id", reason)

        ok, reason = self.controller.validate_listing({"id": "123"})
        self.assertFalse(ok)
        self.assertIn("Missing listing title", reason)

    def test_validate_listing_non_numeric_and_negative_prices(self):
        """Price fields must be numeric integers, canon > 0, admin >= 0."""
        prop = dict(self.valid_base)
        prop["canon"] = "cien mil pesos"
        ok, reason = self.controller.validate_listing(prop)
        self.assertFalse(ok)
        self.assertIn("must be numeric integers", reason)

        prop["canon"] = 0
        ok, reason = self.controller.validate_listing(prop)
        self.assertFalse(ok)
        self.assertIn("Canon must be positive", reason)

        prop["canon"] = 2000000
        prop["admin_fee"] = -50000
        ok, reason = self.controller.validate_listing(prop)
        self.assertFalse(ok)
        self.assertIn("Admin fee cannot be negative", reason)

    def test_validate_listing_price_ceiling_boundary_2500000_vs_2500001(self):
        """Total price exactly $2.500.000 COP passes; $2.500.001 COP is rejected."""
        prop = dict(self.valid_base)
        prop["canon"] = 2000000
        prop["admin_fee"] = 500000
        ok, _ = self.controller.validate_listing(prop)
        self.assertTrue(ok)
        self.assertEqual(prop["total_price"], 2500000)

        prop["admin_fee"] = 500001
        ok, reason = self.controller.validate_listing(prop)
        self.assertFalse(ok)
        self.assertIn("exceeds budget ceiling", reason)

    def test_validate_listing_disallowed_municipalities_and_tokens(self):
        """Listings in Soledad or containing disallowed sector tokens are rejected."""
        prop = dict(self.valid_base)
        prop["neighborhood"] = "Soledad"
        ok, reason = self.controller.validate_listing(prop)
        self.assertFalse(ok)
        self.assertIn("external municipality", reason)

        prop["neighborhood"] = "Riomar"
        prop["title"] = "Apartamento cerca a Rebolo con vista al río"
        ok, reason = self.controller.validate_listing(prop)
        self.assertFalse(ok)
        self.assertIn("disallowed municipality or excluded sector", reason)

    def test_validate_listing_mallorquin_puerto_colombia_border_exemption(self):
        """Ciudad Mallorquín listings with 'puerto colombia' in text pass the municipal gate."""
        prop = dict(self.valid_base)
        prop["neighborhood"] = "Ciudad Mallorquín"
        prop["title"] = "Apartamento nuevo en Ciudad Mallorquín cerca a vía Puerto Colombia"
        prop["address"] = "Sector Ciudad Mallorquín"
        prop["url"] = "https://www.metrocuadrado.com/inmueble/ciudad-mallorquin-1"
        ok, reason = self.controller.validate_listing(prop)
        self.assertTrue(ok, f"Mallorquín should be exempted from Puerto Colombia rejection: {reason}")
        self.assertEqual(prop["zone"], "Noroccidente")

    def test_validate_listing_desconocido_neighborhood_whitelist_rules(self):
        """Neighborhood 'desconocido' is accepted if zone is Norte/Noroccidente, rejected otherwise."""
        prop = dict(self.valid_base)
        prop["neighborhood"] = "Desconocido"
        prop["zone"] = "Norte"
        ok, _ = self.controller.validate_listing(prop)
        self.assertTrue(ok)

        prop["zone"] = "Sur"
        ok, reason = self.controller.validate_listing(prop)
        self.assertFalse(ok)
        self.assertIn("outside Barranquilla Norte target sector", reason)

    def test_validate_listing_url_protocols(self):
        """Only http and https protocols are valid; ftp, javascript, and blank fail."""
        prop = dict(self.valid_base)
        for bad_url in ["", "ftp://files.com/p", "javascript:alert(1)", "file:///C:/pass.txt"]:
            prop["url"] = bad_url
            ok, reason = self.controller.validate_listing(prop)
            self.assertFalse(ok)
            self.assertIn("Invalid or unsafe URL protocol", reason)

    def test_validate_listing_numerical_sanitization_branches(self):
        """Tests fallback clamping for area, bedrooms, bathrooms, parking, and stratum."""
        prop = dict(self.valid_base)
        prop["area_m2"] = -10.0
        prop["bedrooms"] = None
        prop["bathrooms"] = "invalid"
        prop["parking"] = -1
        prop["stratum"] = 99  # Invalid stratum (not in 1..6)
        prop["contact"] = None
        prop["images"] = "not-a-list"

        ok, _ = self.controller.validate_listing(prop)
        self.assertTrue(ok)
        self.assertEqual(prop["area_m2"], 0.0)
        self.assertEqual(prop["bedrooms"], 0)
        self.assertEqual(prop["bathrooms"], 1)
        self.assertEqual(prop["parking"], 0)
        self.assertIsNone(prop["stratum"])
        self.assertIsInstance(prop["contact"], dict)
        self.assertIsInstance(prop["images"], list)

    def test_export_json_and_csv_atomic_writes(self):
        """export_json and export_csv write atomically with UTF-8 BOM on CSV."""
        listings = [dict(self.valid_base)]
        listings[0]["description"] = 'Lindo apto con "balcón" y vista,\nen piso alto.'

        self.controller.export_json(listings)
        self.controller.export_csv(listings)

        self.assertTrue(os.path.exists(self.controller.output_json))
        self.assertTrue(os.path.exists(self.controller.output_csv))

        # Check JSON deserialization
        with open(self.controller.output_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["id"], "PIPE-001")

        # Check CSV UTF-8 BOM
        with open(self.controller.output_csv, "rb") as f:
            raw_bytes = f.read()
            self.assertTrue(raw_bytes.startswith(b"\xef\xbb\xbf"), "CSV must have UTF-8-sig BOM header")

    def test_controller_run_end_to_end_with_mock_fallback(self):
        """Exercises PipelineController.run() full pipeline flow and returns metrics dict."""
        fallback_file = self.tmp_path / "test_run_fallback.json"
        mock_data = [
            dict(self.valid_base),
            {
                "id": "EXP-FAIL",
                "title": "Apto Caro",
                "canon": 3000000,
                "admin_fee": 100000,
                "total_price": 3100000,
                "neighborhood": "Riomar",
                "url": "https://metro.com/p2",
            },
        ]
        fallback_file.write_text(json.dumps(mock_data), encoding="utf-8")
        self.controller.fallback_path = str(fallback_file)
        self.controller.offline = True

        metrics = self.controller.run()
        self.assertEqual(metrics["raw_count"], 2)
        self.assertEqual(metrics["valid_count"], 1)
        self.assertEqual(metrics["rejected_ceiling"], 1)
        self.assertEqual(metrics["final_count"], 1)


class TestDeduplicatorTransitivityAndHardGates(unittest.TestCase):
    """Adversarial stress-testing of two-tier deduplication, Union-Find transitivity, and hard gates."""

    def test_normalize_neighborhood_edge_cases(self):
        """Tests diacritics, noise removal, and canonical synonym mappings."""
        self.assertEqual(normalize_neighborhood(None), "desconocido")
        self.assertEqual(normalize_neighborhood("   "), "desconocido")
        self.assertEqual(normalize_neighborhood("Altos de Riomár"), "riomar")
        self.assertEqual(normalize_neighborhood("Sector El Golf Norte"), "el_golf")
        self.assertEqual(normalize_neighborhood("Conjunto Residencial Villa Campestre"), "villa_campestre")
        self.assertEqual(normalize_neighborhood("Horizontes de Miramar"), "miramar")

    def test_compute_canonical_key_bucket_quantization(self):
        """Canonical key applies 5m2 area bucket and 100k COP price bucket."""
        prop = {
            "neighborhood": "Villa Santos",
            "bedrooms": 3,
            "bathrooms": 2,
            "area_m2": 67.2,
            "total_price": 2140000,
        }
        key = compute_canonical_key(prop, area_bucket_size=5, price_bucket_size=100000)
        self.assertEqual(key, "villa_santos_3hab_2ban_65m2_2100000cop")

    def test_calculate_similarity_hard_gates(self):
        """Tests all 6 hard gates returning exactly 0.0."""
        base_a = {
            "neighborhood": "Riomar",
            "bedrooms": 2,
            "bathrooms": 2,
            "total_price": 2000000,
            "area_m2": 70.0,
            "title": "Apto Sorrento",
            "address": "Cra 58 # 90",
            "description": "Lindo",
        }
        base_b = dict(base_a)

        # Gate 1: Neighborhood mismatch
        base_b["neighborhood"] = "Alto Prado"
        self.assertEqual(calculate_similarity(base_a, base_b), 0.0)
        base_b["neighborhood"] = "Riomar"

        # Gate 2: Bedrooms mismatch
        base_b["bedrooms"] = 3
        self.assertEqual(calculate_similarity(base_a, base_b), 0.0)
        base_b["bedrooms"] = 2

        # Gate 3: Bathrooms delta >= 2
        base_b["bathrooms"] = 4
        self.assertEqual(calculate_similarity(base_a, base_b), 0.0)
        base_b["bathrooms"] = 2

        # Gate 4: Price delta > 150.000 COP
        base_b["total_price"] = 2160000
        self.assertEqual(calculate_similarity(base_a, base_b), 0.0)
        base_b["total_price"] = 2000000

        # Gate 5: Conflicting known buildings (Sorrento vs Torino)
        base_a["title"] = "Apartamento en Edificio Sorrento"
        base_b["title"] = "Apartamento en Edificio Torino"
        self.assertEqual(calculate_similarity(base_a, base_b), 0.0)
        base_a["title"] = "Apartamento en Edificio Sorrento"
        base_b["title"] = "Apartamento en Edificio Sorrento"

        # Gate 6: Area delta > 5.0m2 without building match
        base_a["title"] = "Apartamento bonito"
        base_b["title"] = "Apartamento amplio"
        base_b["area_m2"] = 76.0
        self.assertEqual(calculate_similarity(base_a, base_b), 0.0)

    def test_calculate_similarity_bonus_scores_and_upper_clamp(self):
        """Tests building token bonus (+0.10), street bonus (+0.08), and 1.0 clamping."""
        prop_a = {
            "neighborhood": "Miramar",
            "bedrooms": 2,
            "bathrooms": 2,
            "total_price": 1800000,
            "area_m2": 60.0,
            "title": "Apto en Sorrento cra 43",
            "address": "Cra 43 # 98",
            "description": "Edificio Sorrento",
        }
        prop_b = dict(prop_a)

        sim = calculate_similarity(prop_a, prop_b)
        self.assertEqual(sim, 1.0, "Identical listing with building bonus must clamp to 1.0")

        # Test street match bonus when building token is absent
        prop_c = {
            "neighborhood": "Miramar",
            "bedrooms": 2,
            "bathrooms": 2,
            "total_price": 1800000,
            "area_m2": 60.0,
            "title": "Apartamento lindo",
            "address": "Cra 43 con 99",
            "description": "Muy fresco en cra 43",
        }
        prop_d = {
            "neighborhood": "Miramar",
            "bedrooms": 2,
            "bathrooms": 2,
            "total_price": 1800000,
            "area_m2": 60.0,
            "title": "Apartamento comodo",
            "address": "Sobre la cra 43",
            "description": "Excelente ubicacion en cra 43",
        }
        sim_street = calculate_similarity(prop_c, prop_d)
        self.assertGreaterEqual(sim_street, 0.70)

    def test_deduplicator_transitivity_3_element_chain_consolidated(self):
        """
        Adversarially verifies Union-Find transitivity:
        Listing A matches B (sim >= 0.70), B matches C (sim >= 0.70),
        but sim(A, C) == 0.0 (price delta between A and C is $160k > $150k limit).
        Union-Find MUST merge {A, B, C} into a single canonical cluster!
        """
        listing_a = {
            "id": "MQ-CHAIN-A",
            "portal": "Metrocuadrado",
            "title": "Apto en Miramar piso 4",
            "property_type": "Apartamento",
            "canon": 1800000,
            "admin_fee": 200000,
            "total_price": 2000000,
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "address": "Cra 43 # 98-10",
            "area_m2": 60.0,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "images": ["https://img.com/a.jpg"],
            "url": "https://metro.com/a",
            "contact": {"phone": "3001112233", "whatsapp": "573001112233"},
        }
        listing_b = {
            "id": "FR-CHAIN-B",
            "portal": "Finca Raiz",
            "title": "Apartamento 2 habs Miramar",
            "property_type": "Apartamento",
            "canon": 1880000,
            "admin_fee": 200000,
            "total_price": 2080000,  # delta from A = $80.000 (sim >= 0.70)
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "address": "Cra 43 # 98",
            "area_m2": 60.0,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "images": ["https://img.com/b.jpg"],
            "url": "https://finca.com/b",
            "contact": {"phone": "3001112233", "whatsapp": "573001112233"},
        }
        listing_c = {
            "id": "MQ-CHAIN-C",
            "portal": "Metrocuadrado",
            "title": "Apto Miramar Cra 43",
            "property_type": "Apartamento",
            "canon": 1960000,
            "admin_fee": 200000,
            "total_price": 2160000,  # delta from B = $80.000 (sim >= 0.70), but delta from A = $160.000 (sim = 0.0)
            "neighborhood": "Miramar",
            "zone": "Noroccidente",
            "address": "Cra 43 # 98",
            "area_m2": 60.0,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "images": ["https://img.com/c.jpg"],
            "url": "https://metro.com/c",
            "contact": {"phone": "3001112233", "whatsapp": "573001112233"},
        }

        # Verify pairwise relationships
        self.assertGreaterEqual(calculate_similarity(listing_a, listing_b), 0.70)
        self.assertGreaterEqual(calculate_similarity(listing_b, listing_c), 0.70)
        self.assertEqual(calculate_similarity(listing_a, listing_c), 0.0, "A and C directly violate $150k price gate")

        deduped, stats = deduplicate_listings([listing_a, listing_b, listing_c])
        self.assertEqual(len(deduped), 1, "Transitive chain {A, B, C} must collapse into exactly 1 cluster")
        self.assertEqual(stats["merged_duplicates"], 2)
        self.assertEqual(stats["clusters_formed"], 1)

        merged = deduped[0]
        self.assertEqual(merged["total_price"], 2000000, "Must choose tenant-optimal minimum price ($2.000.000)")
        self.assertEqual(len(merged["images"]), 3, "Images union preserved across cluster")

    def test_merge_cluster_single_item_and_cross_portal_id(self):
        """Single-item clusters return unmodified; multi-item cross-portal clusters create MERGED- id."""
        item = {"id": "MQ-SOLO", "portal": "Metrocuadrado", "total_price": 1500000}
        self.assertEqual(merge_cluster([item]), item)

        p1 = {"id": "MQ-999", "portal": "Metrocuadrado", "total_price": 2000000, "images": ["http://img1?w=100"]}
        p2 = {"id": "FR-888", "portal": "Finca Raiz", "total_price": 2000000, "images": ["http://img1?w=200", "http://img2"]}
        merged = merge_cluster([p1, p2])
        self.assertEqual(merged["id"], "MERGED-999-888")
        self.assertEqual(merged["portal"], "Metrocuadrado + Finca Raiz")
        self.assertEqual(len(merged["images"]), 2, "Duplicate base image URL must be deduplicated")

    def test_deduplicate_listings_empty_input(self):
        """deduplicate_listings on empty input returns ([], zero stats)."""
        res, stats = deduplicate_listings([])
        self.assertEqual(res, [])
        self.assertEqual(stats["input"], 0)
        self.assertEqual(stats["output"], 0)


class TestDashboardServerHardening(unittest.TestCase):
    """Adversarial stress-testing of run_dashboard.py HTTP server and tracking store."""

    @classmethod
    def setUpClass(cls):
        os.environ["DASHBOARD_QUIET"] = "1"
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_tracking_file = Path(cls.temp_dir.name) / "test_user_tracking.json"
        set_tracking_file_path(cls.test_tracking_file)

        # Launch server using ephemeral port 0 (OS allocation)
        cls.server, cls.actual_port = create_server(host="127.0.0.1", port=0)
        cls.base_url = f"http://127.0.0.1:{cls.actual_port}"
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.15)

    @classmethod
    def tearDownClass(cls):
        set_tracking_file_path(None)
        try:
            cls.server.shutdown()
            cls.server.server_close()
        except Exception:
            pass
        cls.temp_dir.cleanup()

    def test_tracking_file_proxy_dunder_methods(self):
        """_TrackingFileProxy implements __fspath__, __str__, __repr__, __getattr__, and __truediv__."""
        self.assertEqual(os.fspath(TRACKING_FILE), str(self.test_tracking_file))
        self.assertEqual(str(TRACKING_FILE), str(self.test_tracking_file))
        self.assertEqual(repr(TRACKING_FILE), repr(self.test_tracking_file))
        child = TRACKING_FILE / "sub.json"
        self.assertEqual(str(child), str(self.test_tracking_file / "sub.json"))

    def test_port_auto_allocation_limits_and_exhaustion(self):
        """find_free_port and create_server raise RuntimeError when attempts are exhausted."""
        with self.assertRaises(RuntimeError):
            find_free_port(start_port=8900, max_attempts=0)

        # Occupy a port with an active socket and assert create_server fails when max_attempts=1
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        occupied_port = s.getsockname()[1]
        try:
            with self.assertRaises(RuntimeError):
                create_server(host="127.0.0.1", port=occupied_port, max_attempts=1)
        finally:
            s.close()

    def test_load_tracking_data_corrupted_disk_recovery(self):
        """load_tracking_data recovers cleanly with default dictionary if JSON file is corrupted."""
        self.test_tracking_file.write_text("{corrupt: json content", encoding="utf-8")
        data = load_tracking_data()
        self.assertEqual(data["version"], "1.0")
        self.assertIsInstance(data["properties"], dict)

        # Test recovery when file holds non-dictionary JSON
        self.test_tracking_file.write_text("[1, 2, 3]", encoding="utf-8")
        data2 = load_tracking_data()
        self.assertIsInstance(data2["properties"], dict)

    def test_update_tracking_state_type_error_and_sync_logic(self):
        """update_tracking_state raises TypeError on non-dict and syncs collection pills."""
        with self.assertRaises(TypeError):
            update_tracking_state(["not a dict"])

        # Update with single property_id where status='favorito' automatically sets favorite=True
        state = update_tracking_state({
            "property_id": "MQ-TEST-FAV",
            "status": "favorito",
            "notes": "Excelente opcion",
        })
        self.assertIn("MQ-TEST-FAV", state["favorites"])
        self.assertTrue(state["properties"]["MQ-TEST-FAV"]["favorite"])

        # Update with bulk properties dictionary containing non-dict element (should be ignored safely)
        state2 = update_tracking_state({
            "properties": {
                "MQ-VISIT": {"status": "visita_programada"},
                "MQ-BAD": "invalid string value",
            }
        })
        self.assertIn("MQ-VISIT", state2["visits"])
        self.assertNotIn("MQ-BAD", state2["properties"])

    def test_http_options_method_returns_204_and_cors_headers(self):
        """OPTIONS / returns 204 No Content with permissive CORS headers."""
        req = urllib.request.Request(f"{self.base_url}/api/tracking", method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 204)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
            self.assertIn("GET", resp.headers.get("Access-Control-Allow-Methods", ""))
            self.assertIn("POST", resp.headers.get("Access-Control-Allow-Methods", ""))

    def test_http_head_method_or_unhandled_methods(self):
        """BaseHTTPRequestHandler returns 501 Unsupported for HEAD or PUT methods."""
        for method in ["HEAD", "PUT", "DELETE"]:
            req = urllib.request.Request(f"{self.base_url}/", method=method)
            try:
                urllib.request.urlopen(req)
                self.fail(f"Method {method} should return 501")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 501)

    def test_static_file_directory_traversal_blocked(self):
        """Requests attempting directory traversal outside WEB_DIR return 403 Forbidden."""
        for attack_path in ["/../run_dashboard.py", "/%2e%2e/data_pipeline/pipeline.py"]:
            req = urllib.request.Request(f"{self.base_url}{attack_path}")
            try:
                urllib.request.urlopen(req)
                self.fail(f"Traversal path {attack_path} should be blocked")
            except urllib.error.HTTPError as e:
                self.assertIn(e.code, (403, 404))

    def test_api_export_csv_and_json(self):
        """GET /api/export handles both csv and json formats with quote escaping."""
        # Seed tracking state with quotes in notes
        update_tracking_state({
            "property_id": "CSV-1",
            "status": "favorito",
            "notes": 'Nota con "comillas dobles" y coma, texto.',
        })

        # Test CSV export
        with urllib.request.urlopen(f"{self.base_url}/api/export?format=csv") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/csv", resp.headers.get("Content-Type", ""))
            content = resp.read().decode("utf-8-sig")
            self.assertIn('""comillas dobles""', content)

        # Test JSON export
        with urllib.request.urlopen(f"{self.base_url}/api/export?format=json") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("CSV-1", data["properties"])

    def test_post_tracking_fuzzing_and_error_codes(self):
        """POST /api/tracking returns HTTP 400 on malformed payloads, non-dict roots, or invalid lengths."""
        post_url = f"{self.base_url}/api/tracking"

        # 1. Non-existent POST endpoint
        req_404 = urllib.request.Request(f"{self.base_url}/api/inexistente", data=b"{}", method="POST")
        try:
            urllib.request.urlopen(req_404)
            self.fail("Should 404 on invalid POST endpoint")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

        # 2. Empty payload (Content-Length: 0)
        req_empty = urllib.request.Request(post_url, data=b"", method="POST")
        try:
            urllib.request.urlopen(req_empty)
            self.fail("Should 400 on empty payload")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
            body = json.loads(e.read().decode("utf-8"))
            self.assertEqual(body["error"], "Empty payload")

        # 3. Invalid UTF-8 bytes
        req_bad_utf = urllib.request.Request(
            post_url,
            data=b"\x80\x81\x82",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req_bad_utf)
            self.fail("Should 400 on invalid UTF-8")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
            body = json.loads(e.read().decode("utf-8"))
            self.assertEqual(body["error"], "Invalid UTF-8 payload")

        # 4. Malformed JSON syntax
        req_malformed = urllib.request.Request(
            post_url,
            data=b"{bad: json syntax",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req_malformed)
            self.fail("Should 400 on malformed JSON")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
            body = json.loads(e.read().decode("utf-8"))
            self.assertEqual(body["error"], "Invalid JSON in request body")

        # 5. Non-dictionary JSON root (e.g. array)
        req_array = urllib.request.Request(
            post_url,
            data=b"[1, 2, 3]",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req_array)
            self.fail("Should 400 on non-dict payload")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
            body = json.loads(e.read().decode("utf-8"))
            self.assertEqual(body["error"], "Payload must be a JSON object")


class TestMFVIAndDossierHardening(unittest.TestCase):
    """Adversarial stress-testing of 100-pt MFVI mathematical model and curated dossier generation."""

    def test_mfvi_zero_price_and_zero_area_division_by_zero_guards(self):
        """Zero area, negative area, or None area safely returns (12.0, 0.0) without ZeroDivisionError."""
        score, cost_m2 = MultiFactorValueIndex.score_price_per_m2(total_price=2000000, area_m2=0)
        self.assertEqual(score, 12.0)
        self.assertEqual(cost_m2, 0.0)

        score, cost_m2 = MultiFactorValueIndex.score_price_per_m2(total_price=0, area_m2=0)
        self.assertEqual(score, 12.0)
        self.assertEqual(cost_m2, 0.0)

        score, cost_m2 = MultiFactorValueIndex.score_price_per_m2(total_price=2000000, area_m2=-15.0)
        self.assertEqual(score, 12.0)
        self.assertEqual(cost_m2, 0.0)

        score, cost_m2 = MultiFactorValueIndex.score_price_per_m2(total_price=2000000, area_m2=None)
        self.assertEqual(score, 12.0)
        self.assertEqual(cost_m2, 0.0)

    def test_mfvi_price_efficiency_brackets(self):
        """Verifies price/m2 efficiency point steps (<28k: 25, <=33k: 21, <=38k: 17, <=44k: 13, >44k: 8)."""
        # cost_m2 = 1.000.000 / 50 = 20.000 (< 28.000) -> 25.0
        s1, c1 = MultiFactorValueIndex.score_price_per_m2(1000000, 50.0)
        self.assertEqual(s1, 25.0)
        self.assertEqual(c1, 20000.0)

        # cost_m2 = 1.500.000 / 50 = 30.000 (<= 33.000) -> 21.0
        s2, c2 = MultiFactorValueIndex.score_price_per_m2(1500000, 50.0)
        self.assertEqual(s2, 21.0)
        self.assertEqual(c2, 30000.0)

        # cost_m2 = 1.800.000 / 50 = 36.000 (<= 38.000) -> 17.0
        s3, c3 = MultiFactorValueIndex.score_price_per_m2(1800000, 50.0)
        self.assertEqual(s3, 17.0)
        self.assertEqual(c3, 36000.0)

        # cost_m2 = 2.000.000 / 50 = 40.000 (<= 44.000) -> 13.0
        s4, c4 = MultiFactorValueIndex.score_price_per_m2(2000000, 50.0)
        self.assertEqual(s4, 13.0)
        self.assertEqual(c4, 40000.0)

        # cost_m2 = 2.500.000 / 50 = 50.000 (> 44.000) -> 8.0
        s5, c5 = MultiFactorValueIndex.score_price_per_m2(2500000, 50.0)
        self.assertEqual(s5, 8.0)
        self.assertEqual(c5, 50000.0)

    def test_mfvi_location_tiers(self):
        """Verifies location scoring tiers in Barranquilla Norte."""
        # Tier A+ (25.0)
        self.assertEqual(MultiFactorValueIndex.score_location("El Golf")[0], 25.0)
        self.assertEqual(MultiFactorValueIndex.score_location("Riomar")[0], 25.0)
        # Tier A (22.0)
        self.assertEqual(MultiFactorValueIndex.score_location("Villa Santos")[0], 22.0)
        self.assertEqual(MultiFactorValueIndex.score_location("Buenavista")[0], 22.0)
        # Tier B+ (18.0)
        self.assertEqual(MultiFactorValueIndex.score_location("Miramar")[0], 18.0)
        self.assertEqual(MultiFactorValueIndex.score_location("Villa Carolina")[0], 18.0)
        # Tier B / default (14.0)
        self.assertEqual(MultiFactorValueIndex.score_location("Otro Sector")[0], 14.0)
        self.assertEqual(MultiFactorValueIndex.score_location(None)[0], 14.0)

    def test_mfvi_stratum_and_amenities_diacritics_and_bounds(self):
        """Verifies stratum scoring and diacritic-insensitive keyword matching capped at 9.0."""
        score, matched = MultiFactorValueIndex.score_stratum_and_amenities(
            stratum=6,
            title="Apto con balcón y piscina",
            description="Edificio con portería 24/7, salón social, planta eléctrica y gimnasio.",
        )
        self.assertEqual(score, 15.0, "Stratum 6 (6.0) + capped amenities (9.0) = 15.0 max")
        self.assertIn("balcon", matched)
        self.assertIn("porteria", matched)
        self.assertIn("planta", matched)

    def test_clean_phone_and_format_cop(self):
        """Tests telephone normalizer and COP currency formatting under edge inputs."""
        self.assertEqual(clean_phone(None), "")
        self.assertEqual(clean_phone(""), "")
        self.assertEqual(clean_phone("3007771690"), "573007771690")
        self.assertEqual(clean_phone("+57 (300) 777-1690"), "573007771690")
        self.assertEqual(clean_phone("573007771690"), "573007771690")

        self.assertEqual(format_cop(None), "$0")
        self.assertEqual(format_cop("invalid"), "$0")
        self.assertEqual(format_cop(0), "$0")
        self.assertEqual(format_cop(2500000), "$2.500.000")
        self.assertEqual(format_cop(1849999.7), "$1.850.000")

    def test_generate_whatsapp_url_encoding(self):
        """generate_whatsapp_url creates valid deep links with encoded parameters."""
        prop = {
            "id": "MQ-1234",
            "property_type": "Apartamento",
            "neighborhood": "Riomar",
            "total_price": 2200000,
            "contact": {"whatsapp": "3001234567"},
        }
        url = generate_whatsapp_url(prop)
        self.assertTrue(url.startswith("https://wa.me/573001234567?text="))
        self.assertIn("MQ-1234", url)
        self.assertIn("Riomar", url)

    def test_select_curated_properties_funnel_and_empty_inputs(self):
        """select_curated_properties filters unqualified listings and caps neighborhood concentration."""
        self.assertEqual(select_curated_properties([]), [])

        # Candidate with < 3 images must be dropped
        unqualified = [
            {
                "id": "UNQ-1",
                "total_price": 2000000,
                "images": ["http://img1.jpg"],  # Only 1 image
                "url": "https://metro.com/1",
                "contact": {"phone": "3001234567"},
                "area_m2": 70,
                "neighborhood": "Riomar",
            }
        ]
        self.assertEqual(select_curated_properties(unqualified), [])

        # Candidate with > $2.5M must be dropped
        expensive = [
            {
                "id": "EXP-1",
                "total_price": 2500001,
                "images": ["1", "2", "3"],
                "url": "https://metro.com/2",
                "contact": {"phone": "3001234567"},
                "area_m2": 70,
                "neighborhood": "Riomar",
            }
        ]
        self.assertEqual(select_curated_properties(expensive), [])

    def test_build_curator_thesis_and_inspection_checklist(self):
        """Thesis and checklist generate robust Spanish sentences tailored to specs."""
        eval_dict = {
            "eval": {
                "mfvi_score": 88.5,
                "tier": "Oro",
                "badge": "Oro",
                "cost_per_m2": 26000,
                "location_tier": "Tier A+",
                "matched_amenities": ["piscina", "ascensor"],
            },
            "neighborhood": "El Golf",
            "area_m2": 95,
            "bedrooms": 3,
            "parking": 1,
            "canon": 2200000,
            "admin_fee": 0,
            "total_price": 2200000,
        }
        thesis = build_curator_thesis(eval_dict)
        self.assertIn("88.5/100", thesis)
        self.assertIn("El Golf", thesis)
        self.assertIn("administración incluida", thesis)

        checklist = build_inspection_checklist(eval_dict)
        self.assertGreaterEqual(len(checklist), 4)
        self.assertTrue(any("Parqueadero privado" in c for c in checklist))

    def test_generate_dossier_markdown_integrity(self):
        """generate_dossier_markdown returns non-empty structured Markdown document."""
        # Use existing curated dataset from data/dossier_curado.json if available
        dossier_json = BASE_DIR / "data" / "dossier_curado.json"
        if dossier_json.exists():
            with open(dossier_json, "r", encoding="utf-8") as f:
                dossier_data = json.load(f)
            props = dossier_data.get("properties", [])
            # Add eval structure for markdown renderer
            for p in props:
                p["eval"] = {
                    "mfvi_score": p.get("mfvi_score", 80.0),
                    "tier": p.get("tier", "Oro"),
                    "badge": "Oro",
                    "cost_per_m2": p.get("cost_per_m2", 28000),
                    "matched_amenities": ["piscina", "porteria"],
                }
            md = generate_dossier_markdown(props, total_db_count=172)
            self.assertIn("# Dossier de Visitas Inmediatas", md)
            self.assertIn("Tabla Maestra Comparativa", md)
            self.assertIn("Itinerario y Ruta Logística", md)


class TestExtractorsAdversarialHardening(unittest.TestCase):
    """Adversarial stress-testing of Metrocuadrado and Finca Raíz stream/SSR parsers."""

    def test_metrocuadrado_clean_neighborhood_name(self):
        """clean_neighborhood_name handles noise tokens, prepositions, and empty strings."""
        self.assertEqual(clean_neighborhood_name(None), "Norte")
        self.assertEqual(clean_neighborhood_name(""), "Norte")
        self.assertEqual(clean_neighborhood_name("altos de riomar barranquilla"), "Altos de Riomar")
        self.assertEqual(clean_neighborhood_name("VILLA SANTOS NORTE"), "Villa Santos")

    def test_metrocuadrado_normalize_whatsapp(self):
        """normalize_whatsapp handles 10 digits, 12 digits, and non-numeric characters."""
        self.assertEqual(normalize_whatsapp(None, "3001234567"), "573001234567")
        self.assertEqual(normalize_whatsapp("3001234567", None), "573001234567")
        self.assertEqual(normalize_whatsapp(None, "573001234567"), "573001234567")
        self.assertEqual(normalize_whatsapp(None, "+57 (300) 123-4567"), "573001234567")

    def test_metrocuadrado_parse_rsc_stream_strategies(self):
        """parse_rsc_stream handles strategy 1 (initialResults), strategy 2 (results:[]), and empty body."""
        extractor = MetrocuadradoExtractor()
        self.assertEqual(extractor.parse_rsc_stream(""), [])

        # Strategy 1: "initialResults":{"results":[{...}]}
        s1 = 'prefix "initialResults":{"total":1,"results":[{"midinmueble":"101"}]} suffix'
        res1 = extractor.parse_rsc_stream(s1)
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0]["midinmueble"], "101")

        # Strategy 2: "results":[{...}]
        s2 = 'prefix "results":[{"midinmueble":"202"}] suffix'
        res2 = extractor.parse_rsc_stream(s2)
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0]["midinmueble"], "202")

        # Malformed JSON inside stream
        s3 = 'prefix "results":[{"midinmueble":unclosed'
        self.assertEqual(extractor.parse_rsc_stream(s3), [])

    def test_metrocuadrado_normalize_property_rejections_and_success(self):
        """normalize_property rejects non-dicts, missing ids, zero price, and over-budget items."""
        extractor = MetrocuadradoExtractor()
        self.assertIsNone(extractor.normalize_property(None))
        self.assertIsNone(extractor.normalize_property({}))  # Missing midinmueble

        # Zero price rejected
        self.assertIsNone(extractor.normalize_property({"midinmueble": "1", "mvalorarriendo": 0}))

        # Price ceiling breach ($2.600.000 COP) rejected
        self.assertIsNone(extractor.normalize_property({"midinmueble": "2", "mvalorarriendo": 2600000}))

        # Valid item normalized
        valid_raw = {
            "midinmueble": "303",
            "mvalorarriendo": 2000000,
            "data": {"mvaloradministracion": 250000},
            "mnombrecomunbarrio": "Riomar",
            "contactPhone": "3007771690",
            "imageLink": "https://img.com/p.jpg",
        }
        item = extractor.normalize_property(valid_raw)
        self.assertIsNotNone(item)
        self.assertEqual(item["id"], "MQ-303")
        self.assertEqual(item["total_price"], 2250000)
        self.assertEqual(item["portal"], "Metrocuadrado")

    def test_fincaraiz_parse_next_data_and_financials(self):
        """FincaRaizExtractor parses SSR __NEXT_DATA__ tag and extracts financials."""
        extractor = FincaRaizExtractor()
        self.assertEqual(extractor.parse_next_data(""), [])
        self.assertEqual(extractor.parse_next_data("<html>No script</html>"), [])

        # Valid SSR HTML payload
        html = """
        <html>
        <script id="__NEXT_DATA__" type="application/json">
        {
          "props": {
            "pageProps": {
              "fetchResult": {
                "searchFast": {
                  "data": [{"id": "FR-100", "price": {"amount": 1800000}}]
                }
              }
            }
          }
        }
        </script>
        </html>
        """
        items = extractor.parse_next_data(html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "FR-100")

        # Test financial extraction with admin_included
        raw_prop = {
            "id": "505",
            "price": {"amount": 1800000, "admin_included": 2100000},
            "commonExpenses": {"amount": 300000},
        }
        canon, admin, total = extractor._extract_financials(raw_prop)
        self.assertEqual(total, 2100000)
        self.assertEqual(canon, 1800000)
        self.assertEqual(admin, 300000)


if __name__ == "__main__":
    unittest.main()
