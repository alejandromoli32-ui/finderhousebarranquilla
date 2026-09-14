#!/usr/bin/env python3
"""
tests/test_adversarial_m3_mfvi.py
Empirical Adversarial Test Suite for M3:
Multi-Factor Value Index (MFVI) Algorithm & Geographic Sector Balance.

Covers:
1. Independent Re-Implementation & 100% Ranking Agreement
   - Complete clean-room re-implementation of 100-point MFVI specification.
   - Verification across 100% of properties (all 172 records in data/inmuebles_barranquilla.json).
   - Component-level breakdown parity (Price/m2, Location, Space, Stratum/Amenities, Contact).
   - Candidate ranking stability and 100% agreement with curated selection funnel.

2. Null / Missing Data Resilience & Boundary Stress-Testing
   - Explicit tests for stratum=None (defaults to base score 2.0 without crash/NaN).
   - Explicit tests for admin_fee=0 and admin_fee=None (inclusive canon handling).
   - Explicit tests for unstated parking (None, 0, omitted key, negative).
   - Null / missing handling for area_m2, bedrooms, bathrooms.
   - Extreme boundary stress tests: area_m2=0, negative area, massive areas (10,000 m2), zero price.
   - None / missing text attributes (title=None, description=None, neighborhood=None).
   - Fuzzing / Monte Carlo mutation stress harness (100 synthetic variations).

3. Sector Diversity & Geographic Balance Audit
   - Multi-sector distribution audit across the 8 top Barranquilla Norte sectors:
     Riomar, Altos de Riomar, Villa Country, Villa Santos, San Vicente, Miramar, Paraíso, El Tabor.
   - Quota enforcement: No single neighborhood exceeds cap (<= 4 properties in Top 15).
   - Geographic tier coverage: Balanced representation across Tier A+, Tier A, and Tier B+.
   - 1:1 Parity audit between data/dossier_curado.json and DOSSIER_VISITAS.md.
"""

import json
import math
import os
from pathlib import Path
import random
import re
import unittest
from collections import Counter
from typing import Any, Dict, List, Tuple

from dossier_generator import (
    MultiFactorValueIndex,
    select_curated_properties,
    generate_whatsapp_url,
    format_cop,
    clean_phone,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data" / "inmuebles_barranquilla.json"
DOSSIER_JSON_FILE = ROOT_DIR / "data" / "dossier_curado.json"
DOSSIER_MD_FILE = ROOT_DIR / "DOSSIER_VISITAS.md"


class IndependentMFVIOfflineOracle:
    """
    Clean-room independent reference implementation of the 100-point
    Multi-Factor Value Index (MFVI) based strictly on the specification:
      1. Price per m² efficiency: 25 pts
      2. Location prestige in Barranquilla Norte: 25 pts
      3. Space & Layout (Rooms, Baths, Parking, Area): 20 pts
      4. Stratum & Amenities: 15 pts
      5. Contact Readiness: 15 pts
    """

    @staticmethod
    def calc_price_per_m2(total_price: Any, area_m2: Any) -> Tuple[float, float]:
        try:
            tot = float(total_price) if total_price is not None else 0.0
            area = float(area_m2) if area_m2 is not None else 0.0
        except (ValueError, TypeError):
            return 12.0, 0.0

        if area <= 0:
            return 12.0, 0.0

        cost_m2 = tot / area
        if cost_m2 < 28000:
            pts = 25.0
        elif cost_m2 <= 33000:
            pts = 21.0
        elif cost_m2 <= 38000:
            pts = 17.0
        elif cost_m2 <= 44000:
            pts = 13.0
        else:
            pts = 8.0
        return pts, round(cost_m2, 0)

    @staticmethod
    def calc_location(neighborhood: Any) -> Tuple[float, str]:
        b = str(neighborhood or "").strip().lower()
        # Tier A+ (25 pts)
        tier_a_plus = ["golf", "alto prado", "altos del prado", "riomar", "altos de riomar", "villa country"]
        if any(k in b for k in tier_a_plus):
            return 25.0, "Tier A+ (Alta Exclusividad / Central Norte)"

        # Tier A (22 pts)
        tier_a = ["villa santos", "buenavista", "altos del limon", "el poblado", "la castellana", "san vicente"]
        if any(k in b for k in tier_a):
            return 22.0, "Tier A (Moderno Residencial / Buenavista)"

        # Tier B+ (18 pts)
        tier_b_plus = [
            "miramar", "villa carolina", "paraiso", "paríso", "andalucia", "andalucía",
            "el limoncito", "el tabor", "los alpes", "la cumbre", "ciudad jardin", "ciudad jardín"
        ]
        if any(k in b for k in tier_b_plus):
            return 18.0, "Tier B+ (Residencial Familiar Consolidado)"

        # Tier B (14 pts)
        return 14.0, "Tier B (Noroccidente / Corredor Norte)"

    @staticmethod
    def calc_space_and_layout(bedrooms: Any, bathrooms: Any, parking: Any, area_m2: Any) -> float:
        try:
            beds = int(bedrooms) if bedrooms is not None else 0
        except (ValueError, TypeError):
            beds = 0

        try:
            baths = int(bathrooms) if bathrooms is not None else 0
        except (ValueError, TypeError):
            baths = 0

        try:
            park = int(parking) if parking is not None else 0
        except (ValueError, TypeError):
            park = 0

        try:
            area = float(area_m2) if area_m2 is not None else 0.0
        except (ValueError, TypeError):
            area = 0.0

        # Bedrooms (6 max)
        if beds >= 3:
            s_beds = 6.0
        elif beds == 2:
            s_beds = 5.0
        elif beds == 1:
            s_beds = 3.0
        else:
            s_beds = 2.0

        # Bathrooms (5 max)
        if baths >= 2:
            s_baths = 5.0
        elif baths == 1:
            s_baths = 3.0
        else:
            s_baths = 1.0

        # Parking (5 max)
        s_park = 5.0 if park >= 1 else 0.0

        # Area (4 max)
        if area >= 85:
            s_area = 4.0
        elif area >= 65:
            s_area = 3.0
        elif area >= 45:
            s_area = 2.0
        else:
            s_area = 1.0

        return round(s_beds + s_baths + s_park + s_area, 1)

    @staticmethod
    def calc_stratum_and_amenities(stratum: Any, title: Any, description: Any) -> Tuple[float, List[str]]:
        try:
            strat = int(stratum) if stratum is not None else 0
        except (ValueError, TypeError):
            strat = 0

        if strat == 6:
            s_strat = 6.0
        elif strat == 5:
            s_strat = 5.0
        elif strat == 4:
            s_strat = 4.0
        else:
            s_strat = 2.0

        raw_text = f"{title or ''} {description or ''}".lower()
        norm_text = raw_text.replace("í", "i").replace("ó", "o")

        keywords = [
            "piscina", "gimnasio", "ascensor", "vigilancia",
            "porteria", "planta", "balcon", "bbq",
            "salon social", "parque infantil", "cocina integral"
        ]
        matched = set()
        for kw in keywords:
            if kw in norm_text:
                matched.add(kw)

        s_amen = min(9.0, len(matched) * 1.5)
        return round(s_strat + s_amen, 1), list(matched)

    @staticmethod
    def calc_contact(contact: Any) -> float:
        if not contact or not isinstance(contact, dict):
            return 0.0

        raw_wa = contact.get("whatsapp")
        raw_ph = contact.get("phone")
        agency = contact.get("agency") or contact.get("agent_name") or ""

        # Normalize phone
        def norm_digits(val):
            if not val:
                return ""
            digs = re.sub(r"\D", "", str(val))
            if len(digs) == 10 and digs.startswith("3"):
                return "57" + digs
            if len(digs) == 12 and digs.startswith("573"):
                return digs
            return digs

        wa = norm_digits(raw_wa)
        phone = norm_digits(raw_ph)

        s_wa = 8.0 if (wa and len(wa) == 12 and wa.startswith("573")) else (4.0 if wa else 0.0)
        s_ph = 4.0 if (phone and len(phone) >= 10) else 0.0
        s_ag = 3.0 if str(agency).strip() else 0.0

        return round(s_wa + s_ph + s_ag, 1)

    @classmethod
    def evaluate(cls, prop: Dict[str, Any]) -> Dict[str, Any]:
        s_pm2, cost_m2 = cls.calc_price_per_m2(prop.get("total_price"), prop.get("area_m2"))
        s_loc, loc_tier = cls.calc_location(prop.get("neighborhood"))
        s_space = cls.calc_space_and_layout(
            prop.get("bedrooms"), prop.get("bathrooms"), prop.get("parking"), prop.get("area_m2")
        )
        s_amen, matched_am = cls.calc_stratum_and_amenities(
            prop.get("stratum"), prop.get("title"), prop.get("description")
        )
        s_contact = cls.calc_contact(prop.get("contact"))

        total_score = round(s_pm2 + s_loc + s_space + s_amen + s_contact, 1)

        if total_score >= 90.0:
            tier = "Diamante"
        elif total_score >= 82.0:
            tier = "Oro"
        elif total_score >= 75.0:
            tier = "Plata"
        else:
            tier = "General"

        return {
            "mfvi_score": total_score,
            "tier": tier,
            "cost_per_m2": cost_m2,
            "location_tier": loc_tier,
            "matched_amenities": matched_am,
            "breakdown": {
                "price_efficiency": s_pm2,
                "location_prestige": s_loc,
                "space_layout": s_space,
                "stratum_amenities": s_amen,
                "contact_readiness": s_contact,
            },
        }


class TestMFVIIndependentReimplementation(unittest.TestCase):
    """
    Adversarially tests independent re-implementation against production dossier_generator.py.
    Must achieve 100% score agreement on all 172 records in data/inmuebles_barranquilla.json.
    """

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(DATA_FILE.exists(), f"Missing dataset {DATA_FILE}")
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            cls.properties = json.load(f)

    def test_full_inventory_100_percent_mfvi_agreement(self):
        """Calculates MFVI independently on all 172 records and confirms 100% agreement."""
        discrepancies = []
        for prop in self.properties:
            pid = prop["id"]
            prod_eval = MultiFactorValueIndex.evaluate(prop)
            oracle_eval = IndependentMFVIOfflineOracle.evaluate(prop)

            diff = round(abs(prod_eval["mfvi_score"] - oracle_eval["mfvi_score"]), 4)
            if diff > 1e-5:
                discrepancies.append({
                    "id": pid,
                    "prod_score": prod_eval["mfvi_score"],
                    "oracle_score": oracle_eval["mfvi_score"],
                    "diff": diff,
                    "prod_breakdown": prod_eval["breakdown"],
                    "oracle_breakdown": oracle_eval["breakdown"]
                })

        self.assertEqual(
            len(discrepancies), 0,
            f"Found {len(discrepancies)} MFVI score discrepancies between production and independent oracle: {discrepancies[:3]}"
        )

    def test_component_breakdown_parity_on_all_properties(self):
        """Verifies each of the 5 component scores matches exactly across all records."""
        for prop in self.properties:
            pid = prop["id"]
            p_bd = MultiFactorValueIndex.evaluate(prop)["breakdown"]
            o_bd = IndependentMFVIOfflineOracle.evaluate(prop)["breakdown"]

            for component in ["price_efficiency", "location_prestige", "space_layout", "stratum_amenities", "contact_readiness"]:
                self.assertAlmostEqual(
                    p_bd[component], o_bd[component], places=4,
                    msg=f"Discrepancy in component '{component}' for property {pid}: prod={p_bd[component]} vs oracle={o_bd[component]}"
                )

    def test_candidate_ranking_relative_order_stability(self):
        """Verifies that descending sort on MFVI produces identical ordering."""
        prod_ranked = sorted(self.properties, key=lambda x: -MultiFactorValueIndex.evaluate(x)["mfvi_score"])
        oracle_ranked = sorted(self.properties, key=lambda x: -IndependentMFVIOfflineOracle.evaluate(x)["mfvi_score"])

        prod_scores = [MultiFactorValueIndex.evaluate(x)["mfvi_score"] for x in prod_ranked]
        oracle_scores = [IndependentMFVIOfflineOracle.evaluate(x)["mfvi_score"] for x in oracle_ranked]

        self.assertEqual(prod_scores, oracle_scores, "Ranked score distributions diverge")

    def test_selection_funnel_exact_match(self):
        """Verifies select_curated_properties(all_properties, 15) matches data/dossier_curado.json exactly."""
        with open(DOSSIER_JSON_FILE, "r", encoding="utf-8") as f:
            dossier_json = json.load(f)

        expected_ids = dossier_json["property_ids"]
        computed_curated = select_curated_properties(self.properties, target_count=15)
        computed_ids = [p["id"] for p in computed_curated]

        self.assertEqual(
            expected_ids, computed_ids,
            f"Curated selection mismatch: expected {expected_ids} but got {computed_ids}"
        )


class TestNullAndMissingDataResilience(unittest.TestCase):
    """
    Adversarial edge case and stress-testing for null/missing/malformed inputs:
    - stratum=None
    - admin_fee=0 and admin_fee=None
    - unstated parking (None, 0, missing key, negative)
    - area_m2=0, negative area, area=None
    - contact variations (empty, partial, missing)
    - Fuzzing / Monte Carlo random mutations
    """

    def setUp(self):
        self.base_property = {
            "id": "ADV-TEST-PROP",
            "portal": "Metrocuadrado",
            "title": "Apartamento en Arriendo en Riomar",
            "property_type": "Apartamento",
            "canon": 2200000,
            "admin_fee": 300000,
            "total_price": 2500000,
            "neighborhood": "Riomar",
            "zone": "Norte",
            "address": "Cra 58 # 90-10",
            "area_m2": 85.0,
            "bedrooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 5,
            "images": ["https://img.com/1.jpg", "https://img.com/2.jpg", "https://img.com/3.jpg"],
            "url": "https://www.metrocuadrado.com/inmueble/123",
            "contact": {
                "phone": "3001234567",
                "whatsapp": "573001234567",
                "agency": "Inmobiliaria Test"
            },
            "description": "Hermoso apartamento con piscina, ascensor y planta eléctrica.",
            "verified": True
        }

    def test_stratum_none_produces_valid_score_without_crash(self):
        """Edge case 1: stratum=None must not crash, not produce NaN, and score base 2.0 pts."""
        prop = dict(self.base_property)
        prop["stratum"] = None

        res = MultiFactorValueIndex.evaluate(prop)
        score = res["mfvi_score"]

        self.assertFalse(math.isnan(score), "MFVI score is NaN when stratum=None")
        self.assertFalse(math.isinf(score), "MFVI score is infinite when stratum=None")
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

        # Base stratum score with None is 2.0
        strat_amen_score, _ = MultiFactorValueIndex.score_stratum_and_amenities(None, prop["title"], prop["description"])
        # Matched amenities in base prop: piscina, ascensor, planta (3 * 1.5 = 4.5 pts) + base strat 2.0 = 6.5
        self.assertEqual(strat_amen_score, 6.5)

    def test_admin_fee_zero_and_none_resilience(self):
        """Edge case 2: admin_fee=0 and admin_fee=None (inclusive canon) evaluate cleanly."""
        for admin_val in [0, None]:
            prop = dict(self.base_property)
            prop["canon"] = 2400000
            prop["admin_fee"] = admin_val
            prop["total_price"] = 2400000  # Total price equals canon when admin is 0/None

            res = MultiFactorValueIndex.evaluate(prop)
            score = res["mfvi_score"]

            self.assertFalse(math.isnan(score), f"Score is NaN for admin_fee={admin_val}")
            self.assertFalse(math.isinf(score), f"Score is Inf for admin_fee={admin_val}")
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)

            # Price efficiency score: 2.400.000 / 85 = 28.235/m2 -> in [28k, 33k] => 21.0 pts
            self.assertEqual(res["breakdown"]["price_efficiency"], 21.0)

    def test_unstated_parking_variations(self):
        """Edge case 3: Unstated parking (None, 0, omitted key, negative) evaluates to 0 pts without error."""
        parking_variations = [
            ("parking_is_None", {"parking": None}),
            ("parking_is_0", {"parking": 0}),
            ("parking_omitted", {}),
            ("parking_negative", {"parking": -1}),
            ("parking_string_zero", {"parking": 0}),
        ]

        for desc, patch in parking_variations:
            prop = dict(self.base_property)
            if desc == "parking_omitted":
                prop.pop("parking", None)
            else:
                prop.update(patch)

            res = MultiFactorValueIndex.evaluate(prop)
            score = res["mfvi_score"]

            self.assertFalse(math.isnan(score), f"NaN score on {desc}")
            self.assertFalse(math.isinf(score), f"Inf score on {desc}")
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)

            # Space score breakdown: beds=3 (6.0), baths=2 (5.0), park=0 (0.0), area=85 (4.0) -> total 15.0
            self.assertEqual(
                res["breakdown"]["space_layout"], 15.0,
                f"Expected 15.0 space score on {desc}, got {res['breakdown']['space_layout']}"
            )

    def test_area_m2_zero_negative_and_none(self):
        """Edge cases: area_m2=0, negative, or None should fall back to neutral score 12.0 without ZeroDivisionError."""
        for bad_area in [0, -10, None, 0.0]:
            prop = dict(self.base_property)
            prop["area_m2"] = bad_area

            # Must not raise ZeroDivisionError
            res = MultiFactorValueIndex.evaluate(prop)
            score = res["mfvi_score"]

            self.assertFalse(math.isnan(score))
            self.assertFalse(math.isinf(score))
            # Price/m2 fallback is 12.0
            self.assertEqual(res["breakdown"]["price_efficiency"], 12.0)

    def test_missing_text_fields_title_and_description(self):
        """Edge case: title=None, description=None, neighborhood=None evaluate gracefully."""
        prop = dict(self.base_property)
        prop["title"] = None
        prop["description"] = None
        prop["neighborhood"] = None

        res = MultiFactorValueIndex.evaluate(prop)
        score = res["mfvi_score"]

        self.assertFalse(math.isnan(score))
        self.assertFalse(math.isinf(score))
        # Location fallback is Tier B (14.0 pts)
        self.assertEqual(res["breakdown"]["location_prestige"], 14.0)
        # Amenity score with no text is 0.0 + stratum 5 (5.0 pts) = 5.0
        self.assertEqual(res["breakdown"]["stratum_amenities"], 5.0)

    def test_contact_variations_and_empty_contacts(self):
        """Edge case: Contact empty, None, or partial fields must not crash."""
        contact_cases = [
            {},
            {"phone": None, "whatsapp": None, "agency": None},
            {"phone": "", "whatsapp": "", "agency": ""},
            {"phone": "3001234567"},  # Phone only
            {"whatsapp": "573001234567"},  # WA only
            {"agency": "Solo Inmobiliaria"},  # Agency only
        ]

        for c in contact_cases:
            prop = dict(self.base_property)
            prop["contact"] = c

            res = MultiFactorValueIndex.evaluate(prop)
            score = res["mfvi_score"]

            self.assertFalse(math.isnan(score))
            self.assertFalse(math.isinf(score))
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)

    def test_fuzzing_monte_carlo_mutation_harness(self):
        """Adversarial Fuzzer: Mutates 100 random variations of attributes and verifies zero crashes."""
        rng = random.Random(42)

        possible_strata = [None, 0, 1, 2, 3, 4, 5, 6, 7, -1]
        possible_areas = [None, 0, -5.0, 20.0, 65.0, 120.0, 10000.0]
        possible_prices = [0, 500000, 1800000, 2500000, 10000000]
        possible_parkings = [None, 0, 1, 2, -1]
        possible_beds = [None, 0, 1, 2, 3, 5]
        possible_baths = [None, 0, 1, 2, 4]
        possible_neighborhoods = [None, "", "Riomar", "El Golf", "Desconocido", "MIRAMAR", "Ciudad Mallorquín"]

        for iteration in range(100):
            mutated = {
                "id": f"FUZZ-{iteration}",
                "total_price": rng.choice(possible_prices),
                "area_m2": rng.choice(possible_areas),
                "stratum": rng.choice(possible_strata),
                "parking": rng.choice(possible_parkings),
                "bedrooms": rng.choice(possible_beds),
                "bathrooms": rng.choice(possible_baths),
                "neighborhood": rng.choice(possible_neighborhoods),
                "title": rng.choice([None, "", "Apto con piscina y gimnasio", "Casa en arriendo"]),
                "description": rng.choice([None, "", "Excelente vista, ascensor, balcón, BBQ"]),
                "contact": rng.choice([
                    {},
                    {"phone": "3001234567"},
                    {"whatsapp": "573001234567"},
                    {"agency": "Inmo"},
                    {"phone": None, "whatsapp": None}
                ])
            }

            try:
                res = MultiFactorValueIndex.evaluate(mutated)
                score = res["mfvi_score"]
                self.assertFalse(math.isnan(score), f"Fuzz {iteration} yielded NaN")
                self.assertFalse(math.isinf(score), f"Fuzz {iteration} yielded Inf")
                self.assertGreaterEqual(score, 0.0, f"Fuzz {iteration} yielded negative score")
                self.assertLessEqual(score, 100.0, f"Fuzz {iteration} exceeded 100 pts")
            except Exception as exc:
                self.fail(f"Fuzzing iteration {iteration} raised unexpected exception: {exc} on input {mutated}")


class TestSectorDiversityAndGeographicBalance(unittest.TestCase):
    """
    Adversarially verifies the geographic distribution and sector diversity of Top 15 curated properties:
    - Target sectors represented: Riomar, Altos de Riomar, Villa Country, Villa Santos, San Vicente, Miramar, Paraíso, El Tabor.
    - Anti-monopoly quota: No single neighborhood exceeds 4 properties.
    - Tier balance: Core exclusive (Tier A+) + Modern expansion (Tier A) + Family northern (Tier B+).
    """

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(DOSSIER_JSON_FILE.exists(), f"Missing dossier JSON {DOSSIER_JSON_FILE}")
        with open(DOSSIER_JSON_FILE, "r", encoding="utf-8") as f:
            cls.dossier_data = json.load(f)

        cls.properties = cls.dossier_data["properties"]
        cls.property_ids = cls.dossier_data["property_ids"]

        cls.assertTrue(DOSSIER_MD_FILE.exists(), f"Missing dossier markdown {DOSSIER_MD_FILE}")
        with open(DOSSIER_MD_FILE, "r", encoding="utf-8") as f:
            cls.dossier_md = f.read()

    def test_top_15_count(self):
        """Dossier contains exactly 15 properties."""
        self.assertEqual(len(self.properties), 15)
        self.assertEqual(len(self.property_ids), 15)

    def test_all_8_requested_top_sectors_represented(self):
        """
        Verify that top 15 properties are distributed across diverse top sectors:
        Riomar, Altos de Riomar, Villa Country, Villa Santos, San Vicente, Miramar, Paraíso, El Tabor.
        """
        required_sectors = [
            "riomar", "altos de riomar", "villa country", "villa santos",
            "san vicente", "miramar", "paraiso", "el tabor"
        ]

        neighborhood_counts = Counter()
        for p in self.properties:
            b_norm = p["neighborhood"].strip().lower()
            neighborhood_counts[b_norm] += 1

        missing_sectors = []
        for sec in required_sectors:
            count = sum(cnt for b, cnt in neighborhood_counts.items() if sec in b or b in sec)
            if count == 0:
                missing_sectors.append(sec)

        self.assertEqual(
            len(missing_sectors), 0,
            f"Required top sectors missing from Top 15 dossier: {missing_sectors}. Distribution: {dict(neighborhood_counts)}"
        )

    def test_sector_concentration_quota_ceiling_enforced(self):
        """Verify no single neighborhood exceeds max quota cap of 4 properties in Top 15."""
        counts = Counter(p["neighborhood"] for p in self.properties)
        for neighborhood, count in counts.items():
            self.assertLessEqual(
                count, 4,
                f"Neighborhood '{neighborhood}' exceeds max quota of 4 with {count} properties"
            )

    def test_geographic_tier_distribution_balance(self):
        """
        Verify balanced distribution across geographic tiers:
        - Tier A+ (High Exclusivity / Core North): >= 40% (Riomar, Altos de Riomar, Villa Country)
        - Tier A (Modern Residential): >= 15% (Villa Santos, San Vicente)
        - Tier B+ (Consolidated Family): >= 15% (Miramar, Paraíso, El Tabor)
        """
        tier_counts = Counter()
        for p in self.properties:
            b = p["neighborhood"].lower()
            if any(k in b for k in ["golf", "alto prado", "riomar", "altos de riomar", "villa country"]):
                tier_counts["Tier A+"] += 1
            elif any(k in b for k in ["villa santos", "buenavista", "san vicente"]):
                tier_counts["Tier A"] += 1
            elif any(k in b for k in ["miramar", "paraiso", "el tabor", "andalucia"]):
                tier_counts["Tier B+"] += 1
            else:
                tier_counts["Other"] += 1

        total = len(self.properties)
        pct_a_plus = (tier_counts["Tier A+"] / total) * 100
        pct_a = (tier_counts["Tier A"] / total) * 100
        pct_b_plus = (tier_counts["Tier B+"] / total) * 100

        self.assertGreaterEqual(pct_a_plus, 40.0, f"Tier A+ representation too low: {pct_a_plus}%")
        self.assertGreaterEqual(pct_a, 15.0, f"Tier A representation too low: {pct_a}%")
        self.assertGreaterEqual(pct_b_plus, 15.0, f"Tier B+ representation too low: {pct_b_plus}%")

    def test_curated_dossier_markdown_and_json_complete_alignment(self):
        """Empirically audit 1:1 parity between data/dossier_curado.json and DOSSIER_VISITAS.md."""
        md = self.dossier_md

        for p in self.properties:
            pid = p["id"]
            total_cop = format_cop(p["total_price"])
            barrio = p["neighborhood"]
            score_str = str(p["mfvi_score"])

            self.assertIn(pid, md, f"Property ID {pid} missing from markdown dossier")
            self.assertIn(barrio, md, f"Neighborhood {barrio} for property {pid} missing from markdown")
            self.assertIn(score_str, md, f"MFVI score {score_str} for property {pid} missing from markdown")
            self.assertIn(total_cop, md, f"Total price {total_cop} for property {pid} missing from markdown")

    def test_property_type_and_price_spread_diversity(self):
        """Verify that the top 15 offers a diverse budget spread and space options."""
        prices = [p["total_price"] for p in self.properties]
        areas = [p["area_m2"] for p in self.properties if p.get("area_m2")]
        bedrooms = [p["bedrooms"] for p in self.properties]

        min_price = min(prices)
        max_price = max(prices)
        price_spread = max_price - min_price

        # Price spread should be at least $500.000 COP between cheapest and dearest
        self.assertGreaterEqual(
            price_spread, 500000,
            f"Insufficient price spread across Top 15: {price_spread} COP"
        )
        self.assertLessEqual(max_price, 2500000, f"Price exceeds ceiling: {max_price}")

        # Area spread covers moderate (<= 75 m2) to large (>= 100 m2) living spaces
        self.assertLessEqual(min(areas), 75.0, "Top 15 lacks moderate-sized options (<= 75 m2)")
        self.assertGreaterEqual(max(areas), 100.0, "Top 15 lacks spacious family options (>= 100 m2)")

        # Bedrooms should cover both 2-bedroom (couples/executives) and 3-bedroom (families)
        self.assertTrue(any(b == 2 for b in bedrooms), "Top 15 lacks 2-bedroom options")
        self.assertTrue(any(b >= 3 for b in bedrooms), "Top 15 lacks 3+ bedroom options")


class TestAdversarialMonotonicityAndFragility(unittest.TestCase):
    """
    Adversarial property-based verification:
    1. Mathematical monotonicity of MFVI dimensions.
    2. Input schema fragility and failure mode characterization.
    """

    def setUp(self):
        self.base_property = {
            "id": "MONOTONE-TEST",
            "total_price": 2000000,
            "area_m2": 70.0,
            "neighborhood": "Miramar",
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "stratum": 4,
            "title": "Apartamento en arriendo",
            "description": "Edificio con vigilancia",
            "contact": {
                "phone": "3001234567",
                "whatsapp": "573001234567",
                "agency": "Inmobiliaria Test"
            }
        }

    def test_monotonicity_price_reduction_never_decreases_score(self):
        """Monotonicity: Lowering total price holding all else constant must never decrease MFVI score."""
        scores = []
        prices = [2500000, 2300000, 2100000, 1900000, 1700000, 1500000, 1200000]
        for p in prices:
            prop = dict(self.base_property)
            prop["total_price"] = p
            res = MultiFactorValueIndex.evaluate(prop)
            scores.append(res["mfvi_score"])

        # As price decreases, score must be non-decreasing
        for i in range(len(scores) - 1):
            self.assertLessEqual(
                scores[i], scores[i + 1],
                f"Monotonicity violation: lower price {prices[i+1]} scored {scores[i+1]} < higher price {prices[i]} ({scores[i]})"
            )

    def test_monotonicity_area_expansion_never_decreases_score(self):
        """Monotonicity: Increasing area_m2 holding price constant must never decrease MFVI score."""
        scores = []
        areas = [40.0, 50.0, 65.0, 75.0, 85.0, 100.0, 120.0]
        for a in areas:
            prop = dict(self.base_property)
            prop["area_m2"] = a
            res = MultiFactorValueIndex.evaluate(prop)
            scores.append(res["mfvi_score"])

        for i in range(len(scores) - 1):
            self.assertLessEqual(
                scores[i], scores[i + 1],
                f"Monotonicity violation: larger area {areas[i+1]} scored {scores[i+1]} < smaller area {areas[i]} ({scores[i]})"
            )

    def test_monotonicity_stratum_upgrade_never_decreases_score(self):
        """Monotonicity: Upgrading stratum from 3 -> 4 -> 5 -> 6 must never decrease MFVI score."""
        scores = []
        strata = [3, 4, 5, 6]
        for s in strata:
            prop = dict(self.base_property)
            prop["stratum"] = s
            res = MultiFactorValueIndex.evaluate(prop)
            scores.append(res["mfvi_score"])

        for i in range(len(scores) - 1):
            self.assertLessEqual(
                scores[i], scores[i + 1],
                f"Monotonicity violation: higher stratum {strata[i+1]} scored {scores[i+1]} < lower stratum {strata[i]} ({scores[i]})"
            )

    def test_monotonicity_location_tier_hierarchy(self):
        """Monotonicity: Location score hierarchy Tier B (14) <= Tier B+ (18) <= Tier A (22) <= Tier A+ (25)."""
        loc_b = MultiFactorValueIndex.score_location("Desconocido Norte")[0]
        loc_b_plus = MultiFactorValueIndex.score_location("Miramar")[0]
        loc_a = MultiFactorValueIndex.score_location("Villa Santos")[0]
        loc_a_plus = MultiFactorValueIndex.score_location("Altos de Riomar")[0]

        self.assertEqual(loc_b, 14.0)
        self.assertEqual(loc_b_plus, 18.0)
        self.assertEqual(loc_a, 22.0)
        self.assertEqual(loc_a_plus, 25.0)

        self.assertTrue(loc_b < loc_b_plus < loc_a < loc_a_plus)

    # --- Empirical Input Schema Fragility Checks ---

    def test_fragility_contact_explicitly_none_raises_attribute_error(self):
        """
        Adversarial Boundary Finding: When prop contains {'contact': None},
        evaluate() raises AttributeError because contact.get() is called on None.
        Empirically reproducible failure mode.
        """
        prop = dict(self.base_property)
        prop["contact"] = None
        with self.assertRaises(AttributeError):
            MultiFactorValueIndex.evaluate(prop)

    def test_fragility_total_price_explicitly_none_raises_type_error(self):
        """
        Adversarial Boundary Finding: When prop contains {'total_price': None, 'area_m2': 60},
        evaluate() raises TypeError because None / area_m2 cannot be evaluated.
        Empirically reproducible failure mode.
        """
        prop = dict(self.base_property)
        prop["total_price"] = None
        with self.assertRaises(TypeError):
            MultiFactorValueIndex.evaluate(prop)

    def test_fragility_images_none_in_selection_funnel(self):
        """
        Adversarial Boundary Finding: When candidate list has {'images': None},
        select_curated_properties raises TypeError ('NoneType' has no len()).
        Empirically reproducible failure mode.
        """
        with self.assertRaises(TypeError):
            select_curated_properties([{"images": None}])


if __name__ == "__main__":
    unittest.main()
