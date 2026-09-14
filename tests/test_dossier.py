#!/usr/bin/env python3
"""
tests/test_dossier.py
Unit and Integration Test Suite for Milestone 3 (M3): Curated Immediate Visit Dossier & Contact Sheets.

Verifies:
  1. Dossier property count is between 10 and 15 properties.
  2. All curated properties strictly satisfy total_price <= 2.500.000 COP and canon + admin == total.
  3. All curated properties belong to Barranquilla Norte / Noroccidente.
  4. All curated properties possess valid direct portal URLs and verified contact phone / WhatsApp.
  5. 100-point Multi-Factor Value Index (MFVI) algorithm calculation and score thresholds (>= 75 pts).
  6. Generated DOSSIER_VISITAS.md contains executive summary, comparative table, factsheets, inspection checklist, and 4-day visit itinerary.
  7. Consistency and integration between data/dossier_curado.json, database, and web dashboard components.
"""

import json
import os
from pathlib import Path
import re
import unittest
import urllib.parse

from dossier_generator import (
    MultiFactorValueIndex,
    select_curated_properties,
    generate_whatsapp_url,
    format_cop,
    clean_phone,
    build_curator_thesis,
    build_inspection_checklist,
    generate_dossier_markdown
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data" / "inmuebles_barranquilla.json"
DOSSIER_JSON_FILE = ROOT_DIR / "data" / "dossier_curado.json"
DOSSIER_MD_FILE = ROOT_DIR / "DOSSIER_VISITAS.md"
INDEX_HTML_FILE = ROOT_DIR / "web" / "index.html"
APP_JS_FILE = ROOT_DIR / "web" / "app.js"

BARRANQUILLA_NORTE_SECTORS = {
    "altos de riomar", "riomar", "alto prado", "altos del prado", "el golf",
    "villa country", "villa santos", "buenavista", "altos del limon", "altos del limón",
    "el poblado", "la castellana", "san vicente", "miramar", "villa carolina",
    "paraiso", "paraíso", "andalucia", "andalucía", "el limoncito", "el tabor",
    "los alpes", "la cumbre", "ciudad jardin", "ciudad jardín", "tabor",
    "ciudad mallorquin", "ciudad mallorquín", "la campiña", "el recreo", "boston",
    "las delicias", "betania", "conjunto residencial villa campestre", "granadillo"
}


class TestCuratedVisitDossier(unittest.TestCase):
    """Test suite for Requirement R3 - Curated Visit Dossier & MFVI System."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(DATA_FILE.exists(), f"Missing dataset {DATA_FILE}")
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            cls.all_properties = json.load(f)

        cls.assertTrue(DOSSIER_JSON_FILE.exists(), f"Missing dossier JSON {DOSSIER_JSON_FILE}")
        with open(DOSSIER_JSON_FILE, "r", encoding="utf-8") as f:
            cls.dossier_data = json.load(f)

        cls.assertTrue(DOSSIER_MD_FILE.exists(), f"Missing dossier markdown {DOSSIER_MD_FILE}")
        with open(DOSSIER_MD_FILE, "r", encoding="utf-8") as f:
            cls.dossier_md = f.read()

    # 1. Count Bounds Test
    def test_dossier_count_bounds(self):
        """Verifies that the curated dossier contains between 10 and 15 standout properties."""
        curated_ids = self.dossier_data.get("property_ids", [])
        curated_props = self.dossier_data.get("properties", [])

        self.assertGreaterEqual(len(curated_ids), 10, "Dossier must contain at least 10 properties")
        self.assertLessEqual(len(curated_ids), 15, "Dossier must not exceed 15 properties")
        self.assertEqual(len(curated_ids), len(curated_props), "IDs and properties length mismatch in JSON")
        self.assertEqual(len(curated_ids), len(set(curated_ids)), "Curated dossier contains duplicate property IDs")

        # Test generation function directly
        computed_curated = select_curated_properties(self.all_properties, target_count=15)
        self.assertGreaterEqual(len(computed_curated), 10)
        self.assertLessEqual(len(computed_curated), 15)

    # 2. Strict Price Ceiling Test
    def test_dossier_price_ceiling_strict(self):
        """Verifies that ALL curated properties satisfy total_price <= 2.500.000 COP and canon + admin == total."""
        for p in self.dossier_data.get("properties", []):
            pid = p["id"]
            total = p["total_price"]
            canon = p["canon"]
            admin = p.get("admin_fee", 0)

            self.assertLessEqual(
                total, 2500000,
                f"Property {pid} exceeds the 2.5M COP ceiling: {total}"
            )
            self.assertEqual(
                total, canon + admin,
                f"Property {pid} total {total} does not match canon {canon} + admin {admin}"
            )
            self.assertGreater(canon, 0, f"Property {pid} has invalid canon {canon}")
            self.assertGreaterEqual(admin, 0, f"Property {pid} has negative admin fee {admin}")

    # 3. Geographic Membership Test
    def test_dossier_geography_north_only(self):
        """Verifies that all curated properties belong strictly to Barranquilla Norte."""
        for p in self.dossier_data.get("properties", []):
            pid = p["id"]
            barrio = (p.get("neighborhood") or "").strip().lower()
            self.assertTrue(
                any(sec in barrio for sec in BARRANQUILLA_NORTE_SECTORS) or barrio in BARRANQUILLA_NORTE_SECTORS,
                f"Property {pid} in '{barrio}' is outside recognized Barranquilla Norte sectors"
            )

    # 4. Contact Readiness and Valid URLs Test
    def test_dossier_contact_and_urls_validity(self):
        """Verifies that all curated properties possess valid direct URLs and contact phone / WhatsApp."""
        db_map = {p["id"]: p for p in self.all_properties}

        for p in self.dossier_data.get("properties", []):
            pid = p["id"]
            self.assertIn(pid, db_map, f"Curated property {pid} not found in master database")
            db_prop = db_map[pid]

            # URL validation
            url = p.get("url") or db_prop.get("url")
            self.assertTrue(bool(url), f"Property {pid} has empty URL")
            self.assertTrue(
                url.startswith("http://") or url.startswith("https://"),
                f"Property {pid} has invalid URL schema: {url}"
            )
            self.assertTrue(
                any(portal in url.lower() for portal in ["metrocuadrado", "fincaraiz", "ciencuadras"]),
                f"Property {pid} URL does not point to valid portal: {url}"
            )

            # Contact validation
            contact = db_prop.get("contact", {})
            phone = contact.get("phone")
            whatsapp = contact.get("whatsapp")
            self.assertTrue(
                bool(phone) or bool(whatsapp),
                f"Property {pid} has neither phone nor WhatsApp contact"
            )

            # WhatsApp URL validation
            wa_url = p.get("whatsapp_url")
            self.assertTrue(bool(wa_url), f"Property {pid} missing generated WhatsApp URL")
            self.assertTrue(
                wa_url.startswith("https://wa.me/"),
                f"Property {pid} WhatsApp URL format invalid: {wa_url}"
            )
            self.assertIn("text=", wa_url, f"Property {pid} WhatsApp URL lacks prefilled message")

    # 5. Multi-Factor Value Index (MFVI) Algorithm Test
    def test_mfvi_scoring_algorithm_and_weights(self):
        """Verifies the MFVI mathematical implementation against the 100-point specification."""
        # Price/m2 efficiency
        s_pm2, cost1 = MultiFactorValueIndex.score_price_per_m2(2000000, 100)  # 20.000/m2 < 28.000
        self.assertEqual(s_pm2, 25.0)
        self.assertEqual(cost1, 20000.0)

        s_pm2_mid, cost2 = MultiFactorValueIndex.score_price_per_m2(2400000, 80)  # 30.000/m2 in [28k, 33k]
        self.assertEqual(s_pm2_mid, 21.0)

        s_pm2_high, cost3 = MultiFactorValueIndex.score_price_per_m2(2500000, 50)  # 50.000/m2 > 44k
        self.assertEqual(s_pm2_high, 8.0)

        # Location scoring
        s_loc1, _ = MultiFactorValueIndex.score_location("El Golf")
        self.assertEqual(s_loc1, 25.0)
        s_loc2, _ = MultiFactorValueIndex.score_location("Altos de Riomar")
        self.assertEqual(s_loc2, 25.0)
        s_loc3, _ = MultiFactorValueIndex.score_location("Villa Santos")
        self.assertEqual(s_loc3, 22.0)
        s_loc4, _ = MultiFactorValueIndex.score_location("Miramar")
        self.assertEqual(s_loc4, 18.0)

        # Space layout scoring
        s_space = MultiFactorValueIndex.score_space_and_layout(bedrooms=3, bathrooms=2, parking=1, area_m2=90)
        # beds: 6, baths: 5, park: 5, area>=85: 4 -> total 20.0
        self.assertEqual(s_space, 20.0)

        # Stratum & amenities
        s_amen, matched = MultiFactorValueIndex.score_stratum_and_amenities(
            stratum=6,
            title="Apartamento con piscina y gimnasio",
            description="Edificio con ascensor, portería y balcón con excelente brisa"
        )
        # Stratum 6: 6.0 pts. Matched: piscina, gimnasio, ascensor, porteria, balcon (5 items * 1.5 = 7.5) -> 13.5
        self.assertGreaterEqual(s_amen, 13.0)
        self.assertIn("piscina", matched)
        self.assertIn("gimnasio", matched)

        # Contact readiness
        s_contact = MultiFactorValueIndex.score_contact_readiness({
            "phone": "3001234567",
            "whatsapp": "573001234567",
            "agency": "Inmobiliaria Barranquilla"
        })
        # WA: 8, Phone: 4, Agency: 3 -> 15.0
        self.assertEqual(s_contact, 15.0)

        # Full evaluation bounds
        sample_prop = {
            "total_price": 2200000,
            "area_m2": 85,
            "neighborhood": "Altos de Riomar",
            "bedrooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 5,
            "title": "Apartamento en arriendo con piscina y ascensor",
            "description": "Excelente cocina integral, vigilancia 24h",
            "contact": {
                "phone": "3101234567",
                "whatsapp": "573101234567",
                "agency": "Inmobiliaria Top"
            }
        }
        res = MultiFactorValueIndex.evaluate(sample_prop)
        self.assertGreaterEqual(res["mfvi_score"], 75.0)
        self.assertLessEqual(res["mfvi_score"], 100.0)
        self.assertIn(res["tier"], ["Diamante", "Oro", "Plata"])

        # Curated items must all score >= 75.0
        for p in self.dossier_data.get("properties", []):
            score = p.get("mfvi_score", 0)
            self.assertGreaterEqual(
                score, 75.0,
                f"Property {p['id']} has MFVI score {score} below quality threshold 75.0"
            )

    # 6. Markdown Document Structure and Completeness Test
    def test_dossier_markdown_sections_and_completeness(self):
        """Verifies that DOSSIER_VISITAS.md contains all required sections, tables, and details."""
        md = self.dossier_md

        # Section headers
        self.assertIn("# Dossier de Visitas Inmediatas", md)
        self.assertIn("1. Resumen Ejecutivo", md)
        self.assertIn("2. Tabla Maestra Comparativa", md)
        self.assertIn("3. Fichas Técnicas Detalladas", md)
        self.assertIn("4. Itinerario y Ruta Logística Sugerida de Visitas", md)
        self.assertIn("5. Protocolo de Arrendamiento", md)

        # Comparative Table
        self.assertIn("| Ref ID |", md)
        self.assertIn("| Score MFVI |", md)
        self.assertIn("| Total Mes |", md)

        # All curated IDs appear in the markdown
        for pid in self.dossier_data.get("property_ids", []):
            self.assertIn(pid, md, f"Curated property {pid} missing from DOSSIER_VISITAS.md")

        # Key elements inside factsheets
        self.assertIn("Desglose Financiero", md)
        self.assertIn("Especificaciones Físicas", md)
        self.assertIn("Tesis del Curador", md)
        self.assertIn("Puntos Críticos a Verificar en la Visita Física", md)
        self.assertIn("wa.me", md)

        # 4-Day Itinerary check
        self.assertIn("Día 1", md)
        self.assertIn("Día 2", md)
        self.assertIn("Día 3", md)
        self.assertIn("Día 4", md)
        self.assertIn("Miércoles", md)
        self.assertIn("Sábado", md)

    # 7. Dashboard Integration and Parity Test
    def test_dashboard_integration_and_parity(self):
        """Verifies that the web dashboard HTML and JS incorporate the Dossier Curado tab and quick action."""
        self.assertTrue(INDEX_HTML_FILE.exists(), "Missing web/index.html")
        self.assertTrue(APP_JS_FILE.exists(), "Missing web/app.js")

        with open(INDEX_HTML_FILE, "r", encoding="utf-8") as f:
            html = f.read()

        with open(APP_JS_FILE, "r", encoding="utf-8") as f:
            js = f.read()

        # HTML checks
        self.assertIn('data-tab="dossier"', html, "index.html missing data-tab='dossier'")
        self.assertIn('id="tabDossier"', html, "index.html missing #tabDossier element")
        self.assertIn('id="countTabDossier"', html, "index.html missing #countTabDossier element")
        self.assertIn('id="dossierQuickBtn"', html, "index.html missing #dossierQuickBtn in header actions")

        # JS checks
        self.assertIn("DEFAULT_DOSSIER_IDS", js, "app.js missing DEFAULT_DOSSIER_IDS definition")
        self.assertIn("dossierIds", js, "app.js missing state.dossierIds container")
        self.assertIn("dossierQuickBtn", js, "app.js missing dossierQuickBtn handler")
        self.assertIn("statusTab === 'dossier'", js, "app.js missing statusTab === 'dossier' filtering")

        # Ensure all dossier property IDs in JSON match master database IDs
        db_ids = {p["id"] for p in self.all_properties}
        for pid in self.dossier_data.get("property_ids", []):
            self.assertIn(pid, db_ids, f"Dossier ID {pid} does not exist in master properties database")

    # 8. WhatsApp Link Prefill Content Test
    def test_whatsapp_prefilled_message_content(self):
        """Verifies that WhatsApp links contain polite, specific inquiries with property ID and price."""
        sample_prop = self.dossier_data["properties"][0]
        wa_url = sample_prop["whatsapp_url"]

        self.assertTrue(wa_url.startswith("https://wa.me/"))
        parsed = urllib.parse.urlparse(wa_url)
        params = urllib.parse.parse_qs(parsed.query)

        self.assertIn("text", params, "WhatsApp URL missing ?text= query parameter")
        msg = params["text"][0]

        self.assertIn(sample_prop["id"], msg, "WhatsApp message does not reference property ID")
        self.assertIn("visita", msg.lower(), "WhatsApp message does not mention visit inquiry")


if __name__ == "__main__":
    unittest.main()
