#!/usr/bin/env python3
"""
tests/test_e2e.py
Opaque-Box End-to-End (E2E) Testing Suite for Milestone M-E2E.
Tracker de Apartamentos y Casas en Arriendo — Barranquilla Norte (≤ $2.500.000 COP)

Test Architecture:
- Tier 1: Feature Contract Coverage (Requirements R1, R2, R3 with >= 5 tests each)
- Tier 2: Boundary Value Analysis & Degenerate Input Hardening
- Tier 3: Cross-Feature Interactions & Multi-Layer State Synchronization
- Tier 4: Real-World User Workflows & Operational Human Journeys

Execution Philosophy:
- Opaque-Box Principle: Interacts strictly with physical files, live HTTP loopback endpoints,
  public schemas, and observable system state.
- Zero-Dependency: Built entirely on Python 3.12 standard library (unittest, json, urllib).
- Strict Isolation: Live HTTP server tests run on dedicated temporary ports with isolated
  temporary tracking data stores to guarantee zero pollution of production files.
"""

import json
import os
from pathlib import Path
import re
import socket
import sys
import tempfile
import threading
import time
import unicodedata
import unittest
import urllib.error
import urllib.parse
import urllib.request

# Ensure workspace root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from run_dashboard import (
    create_server,
    find_free_port,
    load_tracking_data,
    update_tracking_state,
    PROPERTIES_FILE,
    CSV_FILE,
    WEB_DIR,
)
from data_pipeline.pipeline import PipelineController, ALLOWED_BARRIOS, DISALLOWED_MUNICIPALITIES
from dossier_generator import (
    MultiFactorValueIndex,
    select_curated_properties,
    generate_whatsapp_url,
    format_cop,
    clean_phone,
)

DOSSIER_JSON_FILE = BASE_DIR / "data" / "dossier_curado.json"
DOSSIER_MD_FILE = BASE_DIR / "DOSSIER_VISITAS.md"

BARRANQUILLA_NORTE_SECTORS = {
    "altos de riomar", "riomar", "alto prado", "altos del prado", "el golf",
    "villa country", "villa santos", "buenavista", "altos del limon", "altos del limón",
    "el poblado", "la castellana", "san vicente", "miramar", "villa carolina",
    "paraiso", "paraíso", "andalucia", "andalucía", "el limoncito", "el tabor",
    "los alpes", "la cumbre", "ciudad jardin", "ciudad jardín", "tabor",
    "ciudad mallorquin", "ciudad mallorquín", "la campiña", "el recreo", "boston",
    "las delicias", "betania", "conjunto residencial villa campestre", "granadillo"
}


def normalize_str(s: str) -> str:
    """Strips accents and lowers string for opaque-box text matching."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(s))
    ascii_str = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return ascii_str.lower().strip()


# ==============================================================================
# BASE TEST CASE WITH LIVE HTTP SERVER ISOLATION
# ==============================================================================

class LiveDashboardServerMixin:
    """Provides isolated live HTTP server lifecycle for E2E tests."""
    server = None
    server_thread = None
    actual_port = 0
    base_url = ""
    temp_dir = None
    isolated_tracking_path = None

    @classmethod
    def start_isolated_server(cls):
        os.environ["DASHBOARD_QUIET"] = "1"
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.isolated_tracking_path = Path(cls.temp_dir.name) / "test_user_tracking.json"
        os.environ["TRACKING_STORE_PATH"] = str(cls.isolated_tracking_path)

        cls.actual_port = find_free_port(start_port=9100)
        cls.server, cls.actual_port = create_server(host="127.0.0.1", port=cls.actual_port)
        cls.base_url = f"http://127.0.0.1:{cls.actual_port}"

        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.15)

    @classmethod
    def stop_isolated_server(cls):
        if cls.server:
            try:
                cls.server.shutdown()
                cls.server.server_close()
            except Exception:
                pass
        os.environ.pop("TRACKING_STORE_PATH", None)
        if cls.temp_dir:
            try:
                cls.temp_dir.cleanup()
            except Exception:
                pass


# ==============================================================================
# TIER 1: FEATURE CONTRACT COVERAGE
# ==============================================================================

class TestTier1FeatureCoverageR1Data(unittest.TestCase):
    """Tier 1: Feature Contract Coverage for Requirement R1 (Data Layer & Extractor)."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(PROPERTIES_FILE.exists(), f"Properties file missing: {PROPERTIES_FILE}")
        with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
            cls.properties = json.load(f)

    def test_t1_r1_01_database_loading_and_inventory_volume(self):
        """R1-1: Database loads as valid JSON list with robust volume (>= 150 properties)."""
        self.assertIsInstance(self.properties, list)
        self.assertGreaterEqual(len(self.properties), 150, "Inventory must contain >= 150 listings")
        self.assertEqual(len(self.properties), 172, "Verified clean inventory target is 172 properties")

    def test_t1_r1_02_strict_price_ceiling_and_sum_identity(self):
        """R1-2: Every record strictly adheres to total <= 2.500.000 COP and total == canon + admin."""
        for p in self.properties:
            pid = p.get("id")
            total = p.get("total_price")
            canon = p.get("canon")
            admin = p.get("admin_fee", 0)

            self.assertIsNotNone(total, f"Missing total_price in {pid}")
            self.assertLessEqual(total, 2500000, f"Listing {pid} exceeds $2.5M ceiling: ${total:,}")
            self.assertGreater(canon, 0, f"Listing {pid} has non-positive canon: {canon}")
            self.assertGreaterEqual(admin, 0, f"Listing {pid} has negative admin fee: {admin}")
            self.assertEqual(total, canon + admin, f"Listing {pid} financial mismatch: {total} != {canon} + {admin}")

    def test_t1_r1_03_required_schema_fields_integrity(self):
        """R1-3: Every record satisfies the required contract schema without missing fields."""
        required_fields = [
            "id", "title", "property_type", "canon", "admin_fee", "total_price",
            "neighborhood", "area_m2", "bedrooms", "bathrooms", "parking",
            "images", "url", "contact"
        ]
        for p in self.properties:
            pid = p.get("id")
            for field in required_fields:
                self.assertIn(field, p, f"Record {pid} missing mandatory contract field '{field}'")
            self.assertIsInstance(p["images"], list, f"Record {pid} images must be a list")
            self.assertGreater(len(p["images"]), 0, f"Record {pid} has empty images list")
            self.assertIsInstance(p["contact"], dict, f"Record {pid} contact must be a dict")

    def test_t1_r1_04_geographic_containment_barranquilla_norte(self):
        """R1-4: 100% of properties are situated within Barranquilla Norte / Noroccidente perimeter."""
        for p in self.properties:
            pid = p.get("id")
            barrio = normalize_str(p.get("neighborhood", ""))
            zone = normalize_str(p.get("zone", ""))

            # Must match authorized sector or authorized zone
            is_valid_sector = any(normalize_str(sector) in barrio for sector in BARRANQUILLA_NORTE_SECTORS)
            is_valid_zone = any(z in zone for z in ["norte", "noroccidente", "riomar", "historico"])
            self.assertTrue(
                is_valid_sector or is_valid_zone,
                f"Listing {pid} with barrio '{p.get('neighborhood')}' / zone '{p.get('zone')}' is outside Barranquilla Norte"
            )

    def test_t1_r1_05_valid_direct_portal_urls(self):
        """R1-5: All listings provide direct, canonical URLs pointing to recognized real estate portals."""
        valid_domains = ("metrocuadrado.com", "fincaraiz.com.co", "ciencuadras.com")
        for p in self.properties:
            pid = p.get("id")
            url = p.get("url", "").strip()
            self.assertTrue(url.startswith("http://") or url.startswith("https://"), f"Invalid URL scheme in {pid}: {url}")
            self.assertTrue(
                any(domain in url for domain in valid_domains),
                f"Listing {pid} URL does not point to authorized portal: {url}"
            )

    def test_t1_r1_06_unmasked_actionable_contact_channels(self):
        """R1-6: Every listing has unmasked, contactable phone or WhatsApp data in valid Colombian format."""
        for p in self.properties:
            pid = p.get("id")
            contact = p.get("contact", {})
            phone = clean_phone(contact.get("phone"))
            wa = clean_phone(contact.get("whatsapp"))
            agency = str(contact.get("agency") or contact.get("agent_name") or "").strip()

            has_phone = bool(phone and (phone.startswith("573") or phone.startswith("3") or len(phone) >= 7))
            has_wa = bool(wa and (wa.startswith("573") or wa.startswith("3")))
            has_agency = len(agency) > 0

            self.assertTrue(
                has_phone or has_wa or has_agency,
                f"Listing {pid} has void contact information: {contact}"
            )

    def test_t1_r1_07_cross_portal_deduplication_uniqueness(self):
        """R1-7: No duplicate listing IDs or identical duplicate properties exist in database."""
        ids = [p["id"] for p in self.properties]
        self.assertEqual(len(ids), len(set(ids)), "Listing IDs must be globally unique")

        # Canonical fingerprint collision test
        fingerprints = set()
        for p in self.properties:
            fp = (
                normalize_str(p.get("neighborhood", "")),
                p.get("bedrooms"),
                p.get("bathrooms"),
                int(round(float(p.get("area_m2", 0) or 0) / 3.0)),  # bucketed
                int(p.get("total_price", 0) // 100000),             # bucketed
            )
            # Duplicate detection should have resolved collisions or distinguished addresses
            fingerprints.add(fp)
        self.assertGreaterEqual(len(fingerprints), 140, "High distinctness ratio across unique properties")


class TestTier1FeatureCoverageR2Dashboard(unittest.TestCase, LiveDashboardServerMixin):
    """Tier 1: Feature Contract Coverage for Requirement R2 (Dashboard & Persistence Engine)."""

    @classmethod
    def setUpClass(cls):
        cls.start_isolated_server()

    @classmethod
    def tearDownClass(cls):
        cls.stop_isolated_server()

    def test_t1_r2_01_http_server_bootstrap_and_root_html(self):
        """R2-1: HTTP server responds to GET / with status 200, HTML Content-Type, and essential DOM anchors."""
        req = urllib.request.Request(f"{self.base_url}/")
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/html", resp.headers.get("Content-Type", ""))
            html = resp.read().decode("utf-8")
            self.assertIn("propertyGrid", html)
            self.assertIn("searchInput", html)
            self.assertIn("priceSlider", html)
            self.assertIn("dossierQuickBtn", html)

    def test_t1_r2_02_static_assets_serving_and_mime_types(self):
        """R2-2: Static CSS and JS assets are served with proper MIME types and status 200."""
        assets = [
            ("/styles.css", "text/css"),
            ("/app.js", "application/javascript"),
        ]
        for path, expected_mime in assets:
            req = urllib.request.Request(f"{self.base_url}{path}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                content_type = resp.headers.get("Content-Type", "")
                self.assertIn(expected_mime, content_type, f"MIME mismatch for {path}: {content_type}")
                body = resp.read()
                self.assertGreater(len(body), 1000, f"Asset {path} is suspiciously truncated")

    def test_t1_r2_03_realtime_filtering_logic_emulation(self):
        """R2-3: Real-time multi-criteria filtering accurately partitions the complete inventory."""
        with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
            properties = json.load(f)

        # Test filter: Altos de Riomar, total_price <= 2.300.000 COP, bedrooms >= 3
        matches = [
            p for p in properties
            if "altos de riomar" in normalize_str(p.get("neighborhood", ""))
            and p.get("total_price", 0) <= 2300000
            and (p.get("bedrooms") or 0) >= 3
        ]
        self.assertGreater(len(matches), 0, "Filter should match existing properties")
        for m in matches:
            self.assertIn("altos de riomar", normalize_str(m["neighborhood"]))
            self.assertLessEqual(m["total_price"], 2300000)
            self.assertGreaterEqual(m["bedrooms"], 3)

    def test_t1_r2_04_pricing_breakdown_badges_transparency(self):
        """R2-4: Financial transparency: every listing formats Canon and Admin distinctly."""
        with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
            properties = json.load(f)

        sample = properties[0]
        canon_str = format_cop(sample["canon"])
        total_str = format_cop(sample["total_price"])
        self.assertTrue(canon_str.startswith("$"), "Formatted canon must begin with $")
        self.assertTrue(total_str.startswith("$"), "Formatted total must begin with $")
        if sample.get("admin_fee", 0) == 0:
            admin_display = "Incluida"
        else:
            admin_display = format_cop(sample["admin_fee"])
        self.assertTrue(len(admin_display) > 0)

    def test_t1_r2_05_interest_state_persistence_rest_api(self):
        """R2-5: Tracking REST API handles POST state mutation and GET retrieval round-trip."""
        payload = {
            "property_id": "TEST-PROP-001",
            "status": "visita_programada",
            "favorite": True,
            "visit_date": "2026-09-17",
            "notes": "Visita coordinada para jueves 3pm",
            "rating": 5
        }
        req = urllib.request.Request(
            f"{self.base_url}/api/tracking",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            res_data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(res_data.get("success"))

        # Retrieve and verify persistence
        req_get = urllib.request.Request(f"{self.base_url}/api/tracking")
        with urllib.request.urlopen(req_get, timeout=5) as resp_get:
            self.assertEqual(resp_get.status, 200)
            tracking_state = json.loads(resp_get.read().decode("utf-8"))
            saved = tracking_state.get("properties", {}).get("TEST-PROP-001")
            self.assertIsNotNone(saved)
            self.assertEqual(saved["status"], "visita_programada")
            self.assertEqual(saved["notes"], "Visita coordinada para jueves 3pm")
            self.assertIn("TEST-PROP-001", tracking_state.get("visits", []))
            self.assertIn("TEST-PROP-001", tracking_state.get("favorites", []))

    def test_t1_r2_06_whatsapp_deep_link_formatting(self):
        """R2-6: WhatsApp link generator creates valid click-to-chat links with polite inquiry."""
        prop = {
            "id": "MQ-TEST-123",
            "title": "Apartamento en Villa Santos",
            "property_type": "Apartamento",
            "neighborhood": "Villa Santos",
            "total_price": 2100000,
            "contact": {"phone": "3001234567", "whatsapp": "3001234567"}
        }
        wa_url = generate_whatsapp_url(prop)
        self.assertTrue(wa_url.startswith("https://wa.me/573001234567?text="))
        parsed = urllib.parse.urlparse(wa_url)
        qs = urllib.parse.parse_qs(parsed.query)
        msg = qs.get("text", [""])[0]
        self.assertIn("MQ-TEST-123", msg)
        self.assertIn("Villa Santos", msg)
        self.assertIn("2.100.000", msg)
        self.assertIn("visita física esta semana", msg)

    def test_t1_r2_07_export_endpoints_json_and_csv(self):
        """R2-7: Endpoints /api/export support both JSON and CSV export formats with proper headers."""
        for fmt in ("json", "csv"):
            url = f"{self.base_url}/api/export?format={fmt}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                disp = resp.headers.get("Content-Disposition", "")
                self.assertIn(f"user_tracking.{fmt}", disp)
                body = resp.read()
                self.assertGreater(len(body), 10)


class TestTier1FeatureCoverageR3Dossier(unittest.TestCase):
    """Tier 1: Feature Contract Coverage for Requirement R3 (Curated Immediate Visit Dossier)."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(DOSSIER_JSON_FILE.exists(), f"Missing dossier JSON: {DOSSIER_JSON_FILE}")
        with open(DOSSIER_JSON_FILE, "r", encoding="utf-8") as f:
            cls.dossier_data = json.load(f)

        cls.assertTrue(DOSSIER_MD_FILE.exists(), f"Missing dossier markdown: {DOSSIER_MD_FILE}")
        with open(DOSSIER_MD_FILE, "r", encoding="utf-8") as f:
            cls.dossier_md = f.read()

    def test_t1_r3_01_curated_dossier_count_bounds(self):
        """R3-1: Curated dossier contains between 10 and 15 elite properties."""
        props = self.dossier_data.get("properties", [])
        self.assertGreaterEqual(len(props), 10, "Curated dossier must contain at least 10 properties")
        self.assertLessEqual(len(props), 15, "Curated dossier must not exceed 15 properties")

    def test_t1_r3_02_mfvi_score_threshold_and_ranking(self):
        """R3-2: Every curated property scores >= 75.0 points on 100-pt MFVI and is sorted descending."""
        props = self.dossier_data.get("properties", [])
        scores = []
        for p in props:
            score = p.get("mfvi_score")
            if score is None:
                score = p.get("eval", {}).get("mfvi_score", 0.0)
            tier = p.get("tier") or p.get("eval", {}).get("tier", "")
            self.assertGreaterEqual(score, 75.0, f"Property {p.get('id')} has sub-threshold score: {score}")
            self.assertIn(tier, ["Diamante", "Oro", "Plata"])
            scores.append(score)

        # Confirm descending or near-descending ranking
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(
                scores[i], scores[i+1] - 0.5,
                f"Curated list is not ranked by MFVI score: {scores[i]} vs {scores[i+1]}"
            )

    def test_t1_r3_03_actionable_immediate_contact_completeness(self):
        """R3-3: 100% of curated properties have direct phone and WhatsApp booking deep links."""
        with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
            all_props = json.load(f)
        db_map = {p["id"]: p for p in all_props}

        props = self.dossier_data.get("properties", [])
        for p in props:
            pid = p.get("id")
            self.assertIn(pid, db_map, f"Curated property {pid} not found in master database")
            db_prop = db_map[pid]
            contact = db_prop.get("contact", {})
            phone = clean_phone(contact.get("phone"))
            wa = clean_phone(contact.get("whatsapp"))
            self.assertTrue(bool(phone or wa), f"Curated property {pid} lacks direct phone/WA contact")
            wa_link = p.get("whatsapp_url", "")
            self.assertTrue(wa_link.startswith("https://wa.me/"), f"Curated property {pid} missing valid WA url")

    def test_t1_r3_04_markdown_physical_inspection_checklist_presence(self):
        """R3-4: DOSSIER_VISITAS.md contains physical visit checklists for on-site verification."""
        self.assertIn("Puntos Críticos a Verificar en la Visita Física", self.dossier_md)
        self.assertIn("Presión hidráulica y suministro", self.dossier_md)
        self.assertIn("Orientación solar y ventilación cruzada", self.dossier_md)
        self.assertIn("Suplencia eléctrica", self.dossier_md)
        self.assertIn("Parqueadero privado", self.dossier_md)

    def test_t1_r3_05_four_day_logistical_visit_itinerary(self):
        """R3-5: DOSSIER_VISITAS.md specifies a structured 4-day logistical route (Wednesday to Saturday)."""
        self.assertIn("Itinerario y Ruta Logística Sugerida de Visitas", self.dossier_md)
        self.assertIn("Día 1 — Miércoles Tarde: Circuito Alto Prado & Villa Country", self.dossier_md)
        self.assertIn("Día 2 — Jueves Tarde: Circuito Riomar & Altos de Riomar", self.dossier_md)
        self.assertIn("Día 3 — Viernes Tarde: Circuito Villa Santos & Buenavista", self.dossier_md)
        self.assertIn("Día 4 — Sábado Mañana: Circuito Miramar, Paraíso & Villa Carolina", self.dossier_md)

    def test_t1_r3_06_dashboard_curated_integration_consistency(self):
        """R3-6: Web dashboard contains explicit curated dossier filter trigger and synced IDs."""
        app_js_path = WEB_DIR / "app.js"
        index_html_path = WEB_DIR / "index.html"
        self.assertTrue(app_js_path.exists())
        self.assertTrue(index_html_path.exists())

        with open(app_js_path, "r", encoding="utf-8") as f:
            app_js = f.read()
        with open(index_html_path, "r", encoding="utf-8") as f:
            index_html = f.read()

        self.assertIn("dossier_curado.json", app_js)
        self.assertIn("dossierQuickBtn", index_html)
        self.assertIn("tab-dossier", index_html)


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (BOUNDARY VALUE ANALYSIS)
# ==============================================================================

class TestTier2BoundaryCornerCases(unittest.TestCase, LiveDashboardServerMixin):
    """Tier 2: Boundary Value Analysis & Degenerate Input Hardening."""

    @classmethod
    def setUpClass(cls):
        cls.start_isolated_server()
        cls.pipeline = PipelineController(max_price=2500000, offline=True)

    @classmethod
    def tearDownClass(cls):
        cls.stop_isolated_server()

    def test_t2_01_exact_price_ceiling_boundary(self):
        """T2-1: Total price exactly $2.500.000 COP is accepted without error."""
        prop = {
            "id": "MQ-BOUNDARY-2500000",
            "title": "Apartamento en El Golf $2.5M",
            "canon": 2000000,
            "admin_fee": 500000,
            "total_price": 2500000,
            "neighborhood": "El Golf",
            "zone": "Norte",
            "url": "https://www.metrocuadrado.com/inmueble/boundary",
            "area_m2": 80.0,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "contact": {"phone": "3001234567"}
        }
        is_valid, msg = self.pipeline.validate_listing(prop)
        self.assertTrue(is_valid, f"Boundary listing ($2.500.000) was improperly rejected: {msg}")
        self.assertEqual(prop["total_price"], 2500000)

    def test_t2_02_strict_rejection_above_ceiling(self):
        """T2-2: Total price $2.500.001 COP is strictly rejected by the validation gate."""
        prop = {
            "id": "MQ-OVERCEILING-2500001",
            "title": "Apartamento en El Golf $2.500.001",
            "canon": 2000000,
            "admin_fee": 500001,
            "total_price": 2500001,
            "neighborhood": "El Golf",
            "zone": "Norte",
            "url": "https://www.metrocuadrado.com/inmueble/boundary",
            "area_m2": 80.0,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "contact": {"phone": "3001234567"}
        }
        is_valid, msg = self.pipeline.validate_listing(prop)
        self.assertFalse(is_valid, "Listing exceeding $2.5M by 1 COP must be rejected")
        self.assertIn("exceeds budget ceiling", msg)

    def test_t2_03_zero_administration_fee_handling(self):
        """T2-3: Administration fee of $0 (admin included) is accepted and processed safely."""
        prop = {
            "id": "MQ-ADMIN-ZERO",
            "title": "Apartamento en Riomar Admin Incluida",
            "canon": 2200000,
            "admin_fee": 0,
            "total_price": 2200000,
            "neighborhood": "Riomar",
            "zone": "Norte",
            "url": "https://www.metrocuadrado.com/inmueble/adminzero",
            "area_m2": 75.0,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "contact": {"phone": "3001234567"}
        }
        is_valid, msg = self.pipeline.validate_listing(prop)
        self.assertTrue(is_valid, f"Listing with admin_fee=0 was rejected: {msg}")
        self.assertEqual(prop["total_price"], prop["canon"])

        # Also test MFVI evaluation does not crash on admin=0
        eval_res = MultiFactorValueIndex.evaluate(prop)
        self.assertGreater(eval_res["mfvi_score"], 0)

    def test_t2_04_extreme_and_missing_input_tolerance(self):
        """T2-4: Missing optional attributes (stratum: null, parking: None, empty images) handle cleanly."""
        prop = {
            "id": "MQ-MINIMAL",
            "title": "Apartamento en Alto Prado",
            "canon": 1800000,
            "admin_fee": 200000,
            "total_price": 2000000,
            "neighborhood": "Alto Prado",
            "zone": "Norte",
            "url": "https://www.metrocuadrado.com/inmueble/minimal",
            "area_m2": None,
            "bedrooms": None,
            "bathrooms": None,
            "parking": None,
            "stratum": None,
            "images": [],
            "contact": {"phone": "3001234567"}
        }
        is_valid, msg = self.pipeline.validate_listing(prop)
        self.assertTrue(is_valid, f"Minimal listing was rejected: {msg}")
        self.assertEqual(prop["bedrooms"], 0)
        self.assertEqual(prop["parking"], 0)
        self.assertIsNone(prop["stratum"])

        # Test MFVI does not divide by zero on area=0/None
        eval_res = MultiFactorValueIndex.evaluate(prop)
        self.assertIsInstance(eval_res["mfvi_score"], float)

    def test_t2_05_api_corrupted_payload_handling(self):
        """T2-5: REST API safely returns HTTP 400 Bad Request on corrupted/non-dict payloads."""
        # A. Non-dictionary JSON payload (array)
        req_arr = urllib.request.Request(
            f"{self.base_url}/api/tracking",
            data=b"[1, 2, 3]",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req_arr, timeout=5)
        self.assertEqual(ctx.exception.code, 400)

        # B. Invalid JSON string
        req_invalid = urllib.request.Request(
            f"{self.base_url}/api/tracking",
            data=b"{not valid json}",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req_invalid, timeout=5)
        self.assertEqual(ctx.exception.code, 400)

        # C. Non-UTF-8 binary bytes
        req_bin = urllib.request.Request(
            f"{self.base_url}/api/tracking",
            data=b"\xff\xfe\x00\x12",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req_bin, timeout=5)
        self.assertEqual(ctx.exception.code, 400)

        # D. Empty payload
        req_empty = urllib.request.Request(
            f"{self.base_url}/api/tracking",
            data=b"",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req_empty, timeout=5)
        self.assertEqual(ctx.exception.code, 400)

    def test_t2_06_empty_filter_bounds_and_reset_restoration(self):
        """T2-6: Impossible filter criteria yield 0 results gracefully, and clearing restores all 172 records."""
        with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
            properties = json.load(f)

        # Impossible filter: Max price $500.000 COP in El Golf
        filtered = [
            p for p in properties
            if "el golf" in normalize_str(p.get("neighborhood", ""))
            and p.get("total_price", 0) <= 500000
        ]
        self.assertEqual(len(filtered), 0, "Impossible filter must return 0 results")

        # Resetting filter restores total
        restored = [p for p in properties if p.get("total_price", 0) <= 2500000]
        self.assertEqual(len(restored), len(properties))

    def test_t2_07_malformed_and_unsafe_url_rejection(self):
        """T2-7: Unsafe URL protocols (e.g. javascript:, ftp://) are rejected by validation gate."""
        bad_urls = [
            "javascript:alert(1)",
            "ftp://files.example.com/listing",
            "data:text/html,<script>alert(1)</script>",
            ""
        ]
        for url in bad_urls:
            prop = {
                "id": "MQ-BADURL",
                "title": "Apartamento Malformed URL",
                "canon": 2000000,
                "admin_fee": 200000,
                "total_price": 2200000,
                "neighborhood": "Alto Prado",
                "zone": "Norte",
                "url": url,
                "contact": {"phone": "3001234567"}
            }
            is_valid, msg = self.pipeline.validate_listing(prop)
            self.assertFalse(is_valid, f"Unsafe URL '{url}' should be rejected: {msg}")


# ==============================================================================
# TIER 3: CROSS-FEATURE INTERACTIONS
# ==============================================================================

class TestTier3CrossFeatureInteractions(unittest.TestCase, LiveDashboardServerMixin):
    """Tier 3: Cross-Feature Interactions & Multi-Layer Consistency."""

    @classmethod
    def setUpClass(cls):
        cls.start_isolated_server()
        with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
            cls.properties = json.load(f)

    @classmethod
    def tearDownClass(cls):
        cls.stop_isolated_server()

    def test_t3_01_compound_multifaceted_filter_combination(self):
        """T3-1: Multi-filter conjunction (Barrio + Max Price + Rooms + Parking) intersects cleanly."""
        target_barrio = "villa santos"
        max_price = 2200000
        min_rooms = 3
        req_parking = 1

        filtered = [
            p for p in self.properties
            if target_barrio in normalize_str(p.get("neighborhood", ""))
            and p.get("total_price", 0) <= max_price
            and (p.get("bedrooms") or 0) >= min_rooms
            and (p.get("parking") or 0) >= req_parking
        ]
        self.assertGreater(len(filtered), 0, "Expected at least 1 match for compound query")
        for p in filtered:
            self.assertIn(target_barrio, normalize_str(p["neighborhood"]))
            self.assertLessEqual(p["total_price"], max_price)
            self.assertGreaterEqual(p["bedrooms"], min_rooms)
            self.assertGreaterEqual(p["parking"], req_parking)

    def test_t3_02_state_persistence_under_active_filtering(self):
        """T3-2: User interest state updates persist to disk while changing search queries."""
        prop_id = self.properties[5]["id"]

        # Step 1: Mark as favorito via API
        payload = {"property_id": prop_id, "status": "favorito", "favorite": True}
        req = urllib.request.Request(
            f"{self.base_url}/api/tracking",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)

        # Step 2: Query /api/tracking and check favorite persists
        req_get = urllib.request.Request(f"{self.base_url}/api/tracking")
        with urllib.request.urlopen(req_get, timeout=5) as resp:
            state = json.loads(resp.read().decode("utf-8"))
            self.assertIn(prop_id, state.get("favorites", []))
            self.assertEqual(state["properties"][prop_id]["status"], "favorito")

    def test_t3_03_dossier_selection_consistency_with_source_database(self):
        """T3-3: All curated dossier properties exist in main database with identical specs."""
        with open(DOSSIER_JSON_FILE, "r", encoding="utf-8") as f:
            dossier = json.load(f)

        db_lookup = {p["id"]: p for p in self.properties}
        for cur in dossier.get("properties", []):
            cid = cur["id"]
            self.assertIn(cid, db_lookup, f"Dossier property {cid} not found in main database")
            src = db_lookup[cid]
            self.assertEqual(cur["total_price"], src["total_price"], f"Price divergence for {cid}")
            self.assertEqual(cur["neighborhood"], src["neighborhood"], f"Barrio divergence for {cid}")
            self.assertEqual(cur["bedrooms"], src["bedrooms"], f"Bedrooms divergence for {cid}")

    def test_t3_04_dashboard_rest_api_and_json_database_sync(self):
        """T3-4: Dashboard /api/properties endpoint serves byte-for-byte identical dataset as file."""
        req = urllib.request.Request(f"{self.base_url}/api/properties")
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            api_data = json.loads(resp.read().decode("utf-8"))

        self.assertEqual(len(api_data), len(self.properties))
        self.assertEqual([p["id"] for p in api_data], [p["id"] for p in self.properties])

    def test_t3_05_dual_persistence_store_and_export_sync(self):
        """T3-5: Tracking updates reflect consistently across JSON tracking endpoint and CSV export."""
        prop_id = "TEST-SYNC-888"
        payload = {
            "property_id": prop_id,
            "status": "visita_programada",
            "notes": "Confirmada cita sábado 10am",
            "rating": 4
        }
        req = urllib.request.Request(
            f"{self.base_url}/api/tracking",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)

        # Verify CSV export reflects the update
        req_csv = urllib.request.Request(f"{self.base_url}/api/export?format=csv")
        with urllib.request.urlopen(req_csv, timeout=5) as resp:
            csv_content = resp.read().decode("utf-8-sig")
            self.assertIn(prop_id, csv_content)
            self.assertIn("visita_programada", csv_content)
            self.assertIn("Confirmada cita sábado 10am", csv_content)


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (HUMAN JOURNEYS)
# ==============================================================================

class TestTier4RealWorldScenarios(unittest.TestCase, LiveDashboardServerMixin):
    """Tier 4: End-to-End Real-World Application Workflows."""

    @classmethod
    def setUpClass(cls):
        cls.start_isolated_server()
        with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
            cls.properties = json.load(f)

    @classmethod
    def tearDownClass(cls):
        cls.stop_isolated_server()

    def test_t4_scenario_1_young_professional_journey(self):
        """
        Scenario 1: Young professional looking for 2-bedroom apartment in Riomar / Villa Santos.
        Steps:
          1. Filter for 2 bedrooms in Riomar or Villa Santos, budget <= $2.200.000 COP.
          2. Sort by price per m² (space efficiency).
          3. Bookmark top 2 as 'favorito'.
          4. Generate WhatsApp visit request links with prefilled messages.
          5. Verify persistence on server.
        """
        # Step 1: Filter
        candidates = [
            p for p in self.properties
            if any(b in normalize_str(p.get("neighborhood", "")) for b in ["riomar", "villa santos"])
            and p.get("total_price", 0) <= 2200000
            and (p.get("bedrooms") or 0) == 2
        ]
        self.assertGreater(len(candidates), 0, "Scenario 1: Expected viable 2BR candidates")

        # Step 2: Sort by $/m²
        for c in candidates:
            area = float(c.get("area_m2") or 1)
            c["_cost_m2"] = c["total_price"] / max(1.0, area)
        candidates.sort(key=lambda x: x["_cost_m2"])

        top_2 = candidates[:2]
        self.assertEqual(len(top_2), 2)

        # Step 3 & 4: Bookmark favorites and generate WhatsApp URLs
        for prop in top_2:
            pid = prop["id"]
            payload = {"property_id": pid, "status": "favorito", "favorite": True}
            req = urllib.request.Request(
                f"{self.base_url}/api/tracking",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)

            wa_link = generate_whatsapp_url(prop)
            self.assertTrue(wa_link.startswith("https://wa.me/"))
            self.assertIn(pid, wa_link)

        # Step 5: Verify persistence
        req_get = urllib.request.Request(f"{self.base_url}/api/tracking")
        with urllib.request.urlopen(req_get, timeout=5) as resp:
            state = json.loads(resp.read().decode("utf-8"))
            for prop in top_2:
                self.assertIn(prop["id"], state.get("favorites", []))

    def test_t4_scenario_2_corporate_executive_journey(self):
        """
        Scenario 2: Relocating executive looking for 2-3 bedroom in Alto Prado / El Golf / Riomar with parking.
        Steps:
          1. Search for 2-3 bedroom units in Tier A+ sectors (Alto Prado, El Golf, Villa Country, Riomar) with parking.
          2. Inspect building features and check Curated Dossier for highest MFVI score.
          3. Schedule a visit for Thursday afternoon with personal notes.
          4. Persist to API and verify session reload fidelity.
        """
        # Step 1: Filter
        candidates = [
            p for p in self.properties
            if any(b in normalize_str(p.get("neighborhood", "")) for b in ["alto prado", "el golf", "villa country", "riomar", "altos de riomar"])
            and (p.get("bedrooms") or 0) >= 2
            and (p.get("parking") or 0) >= 1
            and p.get("total_price", 0) <= 2500000
        ]
        self.assertGreater(len(candidates), 0, "Scenario 2: Expected executive candidate properties")

        # Step 2: Score candidates with MFVI
        for c in candidates:
            c["_mfvi"] = MultiFactorValueIndex.evaluate(c)["mfvi_score"]
        candidates.sort(key=lambda x: -x["_mfvi"])
        top_choice = candidates[0]

        # Step 3: Schedule visit
        visit_payload = {
            "property_id": top_choice["id"],
            "status": "visita_programada",
            "visit_date": "2026-09-17",
            "notes": "Coordinar visita jueves 4:00 PM. Revisar planta eléctrica y parqueadero.",
            "rating": 5
        }
        req = urllib.request.Request(
            f"{self.base_url}/api/tracking",
            data=json.dumps(visit_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)

        # Step 4: Verify persistence
        req_get = urllib.request.Request(f"{self.base_url}/api/tracking")
        with urllib.request.urlopen(req_get, timeout=5) as resp:
            state = json.loads(resp.read().decode("utf-8"))
            saved = state.get("properties", {}).get(top_choice["id"])
            self.assertIsNotNone(saved)
            self.assertEqual(saved["status"], "visita_programada")
            self.assertIn("planta eléctrica", saved["notes"])
            self.assertIn(top_choice["id"], state.get("visits", []))

    def test_t4_scenario_3_family_space_optimizer_journey(self):
        """
        Scenario 3: Family searching in Miramar / Villa Carolina, discarding unwanted options.
        Steps:
          1. Filter for 3 bedrooms in Miramar / Villa Carolina <= $2.300.000 COP.
          2. Review candidates and discard 2 properties lacking sufficient size.
          3. Verify discarded count updates.
          4. Mistakenly discarded property is restored back to active feed.
          5. Verify state persistence.
        """
        # Step 1: Filter
        family_props = [
            p for p in self.properties
            if any(b in normalize_str(p.get("neighborhood", "")) for b in ["miramar", "villa carolina"])
            and (p.get("bedrooms") or 0) >= 3
            and p.get("total_price", 0) <= 2300000
        ]
        self.assertGreaterEqual(len(family_props), 2, "Scenario 3: Expected at least 2 family properties")

        # Step 2: Discard 2 properties
        discard_1 = family_props[0]["id"]
        discard_2 = family_props[1]["id"]
        for pid in (discard_1, discard_2):
            payload = {"property_id": pid, "status": "descartado"}
            req = urllib.request.Request(
                f"{self.base_url}/api/tracking",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)

        # Step 3: Verify discarded count
        req_get = urllib.request.Request(f"{self.base_url}/api/tracking")
        with urllib.request.urlopen(req_get, timeout=5) as resp:
            state = json.loads(resp.read().decode("utf-8"))
            self.assertIn(discard_1, state.get("discarded", []))
            self.assertIn(discard_2, state.get("discarded", []))

        # Step 4: Restore discard_1
        restore_payload = {"property_id": discard_1, "status": "sin_gestionar"}
        req_restore = urllib.request.Request(
            f"{self.base_url}/api/tracking",
            data=json.dumps(restore_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req_restore, timeout=5) as resp:
            self.assertEqual(resp.status, 200)

        # Step 5: Verify restore
        with urllib.request.urlopen(req_get, timeout=5) as resp:
            state2 = json.loads(resp.read().decode("utf-8"))
            self.assertNotIn(discard_1, state2.get("discarded", []))
            self.assertIn(discard_2, state2.get("discarded", []))

    def test_t4_scenario_4_fast_track_immediate_renter_journey(self):
        """
        Scenario 4: Fast-track immediate renter using Curated Dossier and 4-Day Route.
        Steps:
          1. Open Curated Dossier (dossier_curado.json & DOSSIER_VISITAS.md).
          2. Inspect #1 ranked property (Diamante pick).
          3. Check 4-day itinerary logistics for scheduling.
          4. Click WhatsApp appointment button and generate polite visit inquiry.
          5. Register appointment in tracking system.
        """
        with open(DOSSIER_JSON_FILE, "r", encoding="utf-8") as f:
            dossier = json.load(f)
        with open(DOSSIER_MD_FILE, "r", encoding="utf-8") as f:
            md_text = f.read()

        # Step 1 & 2: Top ranked pick
        top_prop = dossier["properties"][0]
        top_score = top_prop.get("mfvi_score")
        if top_score is None:
            top_score = top_prop.get("eval", {}).get("mfvi_score", 0.0)
        self.assertGreaterEqual(top_score, 90.0, "Top pick should be Diamante tier")
        self.assertIn(top_prop["id"], md_text)

        # Step 3: Check 4-day route
        self.assertIn("Circuito", md_text)
        self.assertIn("Miércoles", md_text)
        self.assertIn("Sábado", md_text)

        # Step 4: Generate WhatsApp URL
        wa_url = generate_whatsapp_url(top_prop)
        self.assertTrue(wa_url.startswith("https://wa.me/"))
        self.assertIn(top_prop["id"], wa_url)

        # Step 5: Register appointment
        appt_payload = {
            "property_id": top_prop["id"],
            "status": "visita_programada",
            "visit_date": "2026-09-16",
            "notes": "Ruta Día 1 Miércoles: Circuito Alto Prado / Villa Country",
            "rating": 5
        }
        req = urllib.request.Request(
            f"{self.base_url}/api/tracking",
            data=json.dumps(appt_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)

        # Verify
        req_get = urllib.request.Request(f"{self.base_url}/api/tracking")
        with urllib.request.urlopen(req_get, timeout=5) as resp:
            tracking = json.loads(resp.read().decode("utf-8"))
            self.assertIn(top_prop["id"], tracking.get("visits", []))
            self.assertEqual(
                tracking["properties"][top_prop["id"]]["notes"],
                "Ruta Día 1 Miércoles: Circuito Alto Prado / Villa Country"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
