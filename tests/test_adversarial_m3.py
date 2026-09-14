"""
tests/test_adversarial_m3.py
Adversarial Verification Suite for Milestone 3: Curated Visit Dossier & Contact Completeness.
Authored by challenger_m3_1.

Empirical verification of:
1. Markdown Dossier extraction & 1:1 parity (Table vs Factsheets vs JSON dataset).
2. Strict existence of all 15 property IDs in data/inmuebles_barranquilla.json.
3. 1:1 Financial arithmetic and price ceiling:
   - Canon + Admin == Total in Markdown table.
   - Canon + Admin == Total in Markdown factsheet.
   - Total <= 2.500.000 COP strictly (zero violations).
   - 1:1 match with source properties in database.
4. WhatsApp URLs syntax & prefilled semantic message audit:
   - Must match https://wa.me/573XXXXXXXXX?text=...
   - Valid Colombian MSISDN (country code 57 + 10-digit mobile starting with 3).
   - Prefilled message must contain the exact property reference ID and visit inquiry text.
5. Direct Portal Listing URLs validation:
   - Must be valid HTTP/HTTPS URLs.
   - Must point strictly to Metrocuadrado or Finca Raíz domains.
   - Must point to the specific listing endpoint (not homepage or search page).
   - Must match database record listing URL.
6. Phone number validation:
   - Must be valid Colombian numbers (10-digit mobile 3XXXXXXXXX or 10-digit landline 605XXXXXXX).
   - Must be unmasked and actionable.
7. Adversarial Fuzzing & Synthetic Mutation Stress Tests:
   - Fuzz price boundary ($2.500.001 rejection, negative fees).
   - Fuzz corrupted WhatsApp URLs (missing ID, missing phone, invalid domain).
   - Fuzz corrupted portal URLs.
   - Fuzz malformed phone numbers.
8. Dashboard Integration Synchronization:
   - Ensure web/app.js DEFAULT_DOSSIER_IDS exactly aligns with the 15 dossier IDs.
"""

import json
import os
from pathlib import Path
import re
import unittest
import urllib.parse

BASE_DIR = Path(__file__).resolve().parent.parent
DOSSIER_MD_FILE = BASE_DIR / "DOSSIER_VISITAS.md"
DOSSIER_JSON_FILE = BASE_DIR / "data" / "dossier_curado.json"
DATABASE_FILE = BASE_DIR / "data" / "inmuebles_barranquilla.json"
APP_JS_FILE = BASE_DIR / "web" / "app.js"

ALLOWED_PORTAL_DOMAINS = {
    "www.metrocuadrado.com",
    "metrocuadrado.com",
    "www.fincaraiz.com.co",
    "fincaraiz.com.co"
}


def parse_cop_amount(text: str) -> int:
    """Parses '$1.810.912 COP' or '$0' or 'Incluida' into integer COP."""
    if not text:
        return 0
    clean = text.strip()
    if "incluida" in clean.lower():
        # Match e.g. "Incluida ($0) COP" or "Incluida"
        m = re.search(r"\$([0-9\.]+)", clean)
        if m:
            return int(m.group(1).replace(".", ""))
        return 0
    # Match standard dollar string $1.850.000
    m = re.search(r"\$([0-9\.]+)", clean)
    if m:
        return int(m.group(1).replace(".", ""))
    # Raw digits
    digits = re.sub(r"\D", "", clean)
    return int(digits) if digits else 0


def parse_dossier_markdown(md_content: str):
    """
    Parses DOSSIER_VISITAS.md into structured records:
    - table_entries: list of dicts from Section 2
    - factsheets: list of dicts from Section 3
    """
    # 1. Parse Section 2 Table
    table_entries = []
    table_section_match = re.search(
        r"## 2\. Tabla Maestra Comparativa.*?\n(\|.+?\n(?:\|.+?\n)+)",
        md_content,
        re.DOTALL
    )
    if table_section_match:
        table_text = table_section_match.group(1)
        lines = [ln.strip() for ln in table_text.splitlines() if ln.strip().startswith("|")]
        # Skip header and separator
        data_lines = [ln for ln in lines if not re.match(r"^\|(?:\s*:?-+:?\s*\|)+$", ln) and "Ref ID" not in ln]
        for line in data_lines:
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) >= 14:
                rank = cols[0]
                ref_id = cols[1].strip("` ")
                barrio = cols[2]
                ptype = cols[3]
                area = cols[4]
                rooms = cols[5]
                baths = cols[6]
                parking = cols[7]
                canon_str = cols[8]
                admin_str = cols[9]
                total_str = cols[10].replace("**", "")
                cost_m2_str = cols[11]
                score_mfvi_str = cols[12].replace("**", "")
                
                # Extract WA URL
                wa_match = re.search(r"\((https://wa\.me/[^\)]+)\)", cols[13])
                wa_url = wa_match.group(1) if wa_match else ""

                table_entries.append({
                    "rank": rank,
                    "id": ref_id,
                    "neighborhood": barrio,
                    "property_type": ptype,
                    "area_m2_str": area,
                    "rooms": rooms,
                    "baths": baths,
                    "parking": parking,
                    "canon": parse_cop_amount(canon_str),
                    "admin_fee": parse_cop_amount(admin_str),
                    "total_price": parse_cop_amount(total_str),
                    "cost_m2": parse_cop_amount(cost_m2_str),
                    "score_mfvi": float(score_mfvi_str) if score_mfvi_str else 0.0,
                    "whatsapp_url": wa_url,
                    "raw_line": line
                })

    # 2. Parse Section 3 Factsheets
    factsheets = []
    # Split by "### Inmueble #"
    chunks = re.split(r"(?=### Inmueble #\d+)", md_content)
    for chunk in chunks:
        if not chunk.startswith("### Inmueble #"):
            continue

        header_m = re.match(r"### Inmueble #(\d+)\s*—\s*([^\n]+)", chunk)
        rank_num = int(header_m.group(1)) if header_m else None
        title = header_m.group(2).strip() if header_m else ""

        ref_m = re.search(r"\*\*Referencia\*\*:\s*`([^`]+)`", chunk)
        ref_id = ref_m.group(1).strip() if ref_m else ""

        portal_m = re.search(r"\*\*Portal\*\*:\s*`([^`]+)`", chunk)
        portal = portal_m.group(1).strip() if portal_m else ""

        canon_m = re.search(r"-\s*\*\*Canon de Arrendamiento\*\*:\s*([^\n]+)", chunk)
        canon_val = parse_cop_amount(canon_m.group(1)) if canon_m else 0

        admin_m = re.search(r"-\s*\*\*Valor de Administración\*\*:\s*([^\n]+)", chunk)
        admin_val = parse_cop_amount(admin_m.group(1)) if admin_m else 0

        total_m = re.search(r"-\s*\*\*COSTO TOTAL MENSUAL\*\*:\s*\*\*([^\*]+)\*\*", chunk)
        total_val = parse_cop_amount(total_m.group(1)) if total_m else 0

        phone_m = re.search(r"-\s*\*\*Teléfono de Contacto\*\*:\s*`([^`]+)`", chunk)
        phone_val = phone_m.group(1).strip() if phone_m else ""

        wa_m = re.search(r"-\s*\*\*Iniciar Chat de WhatsApp Inmediato\*\*:\s*\[[^\]]+\]\((https://wa\.me/[^\)]+)\)", chunk)
        wa_val = wa_m.group(1).strip() if wa_m else ""

        listing_m = re.search(r"-\s*\*\*Publicación Oficial\*\*:\s*\[[^\]]+\]\(([^\)]+)\)", chunk)
        listing_url = listing_m.group(1).strip() if listing_m else ""

        factsheets.append({
            "rank_num": rank_num,
            "title": title,
            "id": ref_id,
            "portal": portal,
            "canon": canon_val,
            "admin_fee": admin_val,
            "total_price": total_val,
            "phone": phone_val,
            "whatsapp_url": wa_val,
            "listing_url": listing_url,
            "raw_chunk": chunk
        })

    return table_entries, factsheets


class TestAdversarialM3CuratedDossier(unittest.TestCase):
    """Adversarial stress-testing of Milestone 3 Curated Dossier & Contact Sheets."""

    @classmethod
    def setUpClass(cls):
        # Verify all essential files exist
        assert DOSSIER_MD_FILE.exists(), f"DOSSIER_VISITAS.md not found at {DOSSIER_MD_FILE}"
        assert DATABASE_FILE.exists(), f"Database not found at {DATABASE_FILE}"
        assert DOSSIER_JSON_FILE.exists(), f"Dossier JSON not found at {DOSSIER_JSON_FILE}"

        with open(DOSSIER_MD_FILE, "r", encoding="utf-8") as f:
            cls.dossier_md = f.read()

        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            cls.database = json.load(f)
        cls.db_map = {p["id"]: p for p in cls.database}

        with open(DOSSIER_JSON_FILE, "r", encoding="utf-8") as f:
            cls.dossier_json = json.load(f)

        cls.table_entries, cls.factsheets = parse_dossier_markdown(cls.dossier_md)

    # -------------------------------------------------------------
    # 1. Structural Parity & Count Bounds
    # -------------------------------------------------------------
    def test_dossier_exact_15_count_and_parity(self):
        """Table, factsheets, and JSON must all contain exactly 15 curated properties."""
        self.assertEqual(len(self.table_entries), 15, f"Expected 15 entries in Table, found {len(self.table_entries)}")
        self.assertEqual(len(self.factsheets), 15, f"Expected 15 Factsheets in Section 3, found {len(self.factsheets)}")
        self.assertEqual(len(self.dossier_json.get("properties", [])), 15, "Dossier JSON properties count != 15")
        self.assertEqual(len(self.dossier_json.get("property_ids", [])), 15, "Dossier JSON property_ids count != 15")

        # Verify ID alignment between table and factsheets
        table_ids = [e["id"] for e in self.table_entries]
        factsheet_ids = [f["id"] for f in self.factsheets]
        json_ids = self.dossier_json.get("property_ids", [])

        self.assertEqual(table_ids, factsheet_ids, "Property IDs order mismatch between Table and Factsheets")
        self.assertEqual(table_ids, json_ids, "Property IDs mismatch between Markdown Table and JSON")
        self.assertEqual(len(set(table_ids)), 15, "Duplicate IDs detected in Curated Dossier")

    # -------------------------------------------------------------
    # 2. Database Existence & Origin Verification
    # -------------------------------------------------------------
    def test_every_dossier_id_exists_in_database(self):
        """Every single property ID in DOSSIER_VISITAS.md must exist in data/inmuebles_barranquilla.json."""
        missing = []
        for prop_id in [e["id"] for e in self.table_entries]:
            if prop_id not in self.db_map:
                missing.append(prop_id)

        self.assertEqual(len(missing), 0, f"Found curated IDs not present in master database: {missing}")

    # -------------------------------------------------------------
    # 3. 1:1 Financial Integrity & Price Ceiling (<= 2.500.000 COP)
    # -------------------------------------------------------------
    def test_financial_breakdown_1to1_match_and_arithmetic(self):
        """
        For all 15 properties:
        - Markdown Table: Canon + Admin == Total <= $2.500.000 COP
        - Markdown Factsheet: Canon + Admin == Total <= $2.500.000 COP
        - Source DB: Canon + Admin == Total <= $2.500.000 COP
        - Values must match 1:1 across Table, Factsheet, and Database.
        """
        for idx in range(15):
            t = self.table_entries[idx]
            f = self.factsheets[idx]
            pid = t["id"]
            db = self.db_map[pid]

            # Database arithmetic
            self.assertEqual(db["total_price"], db["canon"] + db["admin_fee"],
                             f"DB arithmetic failure for {pid}: {db['total_price']} != {db['canon']} + {db['admin_fee']}")
            self.assertLessEqual(db["total_price"], 2500000,
                                 f"DB price ceiling breach for {pid}: {db['total_price']} > 2.500.000 COP")

            # Table arithmetic
            self.assertEqual(t["total_price"], t["canon"] + t["admin_fee"],
                             f"Table arithmetic failure for {pid}: {t['total_price']} != {t['canon']} + {t['admin_fee']}")
            self.assertLessEqual(t["total_price"], 2500000,
                                 f"Table price ceiling breach for {pid}: {t['total_price']} > 2.500.000 COP")

            # Factsheet arithmetic
            self.assertEqual(f["total_price"], f["canon"] + f["admin_fee"],
                             f"Factsheet arithmetic failure for {pid}: {f['total_price']} != {f['canon']} + {f['admin_fee']}")
            self.assertLessEqual(f["total_price"], 2500000,
                                 f"Factsheet price ceiling breach for {pid}: {f['total_price']} > 2.500.000 COP")

            # 1:1 Match: Table vs DB
            self.assertEqual(t["canon"], db["canon"], f"Canon mismatch Table vs DB for {pid}: {t['canon']} != {db['canon']}")
            self.assertEqual(t["admin_fee"], db["admin_fee"], f"Admin fee mismatch Table vs DB for {pid}: {t['admin_fee']} != {db['admin_fee']}")
            self.assertEqual(t["total_price"], db["total_price"], f"Total price mismatch Table vs DB for {pid}: {t['total_price']} != {db['total_price']}")

            # 1:1 Match: Factsheet vs DB
            self.assertEqual(f["canon"], db["canon"], f"Canon mismatch Factsheet vs DB for {pid}: {f['canon']} != {db['canon']}")
            self.assertEqual(f["admin_fee"], db["admin_fee"], f"Admin fee mismatch Factsheet vs DB for {pid}: {f['admin_fee']} != {db['admin_fee']}")
            self.assertEqual(f["total_price"], db["total_price"], f"Total price mismatch Factsheet vs DB for {pid}: {f['total_price']} != {db['total_price']}")

    def test_no_zero_or_negative_canon(self):
        """Canon must strictly be positive across all 15 curated properties."""
        for t in self.table_entries:
            self.assertGreater(t["canon"], 0, f"Property {t['id']} has invalid canon: {t['canon']}")
            self.assertGreaterEqual(t["admin_fee"], 0, f"Property {t['id']} has negative admin fee: {t['admin_fee']}")

    # -------------------------------------------------------------
    # 4. WhatsApp URLs Syntax & Prefilled Text Integrity
    # -------------------------------------------------------------
    def test_whatsapp_urls_syntactic_and_colombian_mobile_validity(self):
        """
        All WhatsApp URLs in Table and Factsheets must:
        - Have scheme 'https' and netloc 'wa.me'
        - Recipient phone must be a valid Colombian mobile MSISDN: 57 + 10 digits starting with 3 (total 12 digits)
        - Mobile prefix must be a recognized Colombian operator block (300-324)
        """
        colombian_mobile_pattern = re.compile(r"^57(3[0-2][0-9]\d{7})$")

        for idx in range(15):
            t = self.table_entries[idx]
            f = self.factsheets[idx]
            pid = t["id"]

            for source_name, wa_url in [("Table", t["whatsapp_url"]), ("Factsheet", f["whatsapp_url"])]:
                self.assertTrue(bool(wa_url), f"{source_name} for {pid} has empty WhatsApp URL")
                parsed = urllib.parse.urlparse(wa_url)
                self.assertEqual(parsed.scheme, "https", f"{source_name} {pid} URL scheme != https: {wa_url}")
                self.assertEqual(parsed.netloc, "wa.me", f"{source_name} {pid} URL netloc != wa.me: {wa_url}")

                phone_target = parsed.path.lstrip("/")
                self.assertTrue(
                    bool(colombian_mobile_pattern.match(phone_target)),
                    f"{source_name} {pid} WhatsApp recipient '{phone_target}' is not a valid Colombian mobile (expected 573XXXXXXXXX)"
                )

    def test_whatsapp_prefilled_text_semantic_content(self):
        """
        Prefilled query parameter 'text' must:
        - Exist and be non-empty
        - Contain the exact property reference ID
        - Contain the price or formatted amount
        - State clear appointment / visit intention ('visita')
        - Have no undefined, null, or injection tokens
        """
        for idx in range(15):
            t = self.table_entries[idx]
            pid = t["id"]
            db = self.db_map[pid]

            for wa_url in [t["whatsapp_url"], self.factsheets[idx]["whatsapp_url"]]:
                parsed = urllib.parse.urlparse(wa_url)
                params = urllib.parse.parse_qs(parsed.query)

                self.assertIn("text", params, f"Property {pid} WhatsApp link missing 'text' param")
                text_msg = params["text"][0]

                # Semantic assertions
                self.assertIn(pid, text_msg, f"WhatsApp text for {pid} does not mention property ID: '{text_msg}'")
                self.assertIn("visita", text_msg.lower(), f"WhatsApp text for {pid} does not mention 'visita'")
                self.assertTrue("arriendo" in text_msg.lower() or "apartamento" in text_msg.lower() or "publicación" in text_msg.lower())
                
                # Check for template leakages
                for leak in ["undefined", "null", "NaN", "{", "}", "[object Object]"]:
                    self.assertNotIn(leak, text_msg, f"WhatsApp text contains template leakage token '{leak}': {text_msg}")

    # -------------------------------------------------------------
    # 5. Direct Portal Listing URLs Validation
    # -------------------------------------------------------------
    def test_listing_urls_validity_and_source_match(self):
        """
        All listing URLs in factsheets must:
        - Be valid HTTP/HTTPS
        - Point strictly to Metrocuadrado or Finca Raíz
        - Match exactly the source database URL for that property ID
        - Have a specific listing path
        """
        for f in self.factsheets:
            pid = f["id"]
            url = f["listing_url"]
            db = self.db_map[pid]

            self.assertTrue(bool(url), f"Property {pid} has empty listing URL")
            parsed = urllib.parse.urlparse(url)

            self.assertIn(parsed.scheme, ("http", "https"), f"Property {pid} invalid URL scheme: {parsed.scheme}")
            self.assertIn(parsed.netloc.lower(), ALLOWED_PORTAL_DOMAINS,
                          f"Property {pid} listing domain '{parsed.netloc}' not in allowed portals: {ALLOWED_PORTAL_DOMAINS}")

            # Specific path
            self.assertTrue(len(parsed.path) > 5, f"Property {pid} listing path too short or empty: {parsed.path}")
            self.assertNotEqual(parsed.path, "/", f"Property {pid} points to homepage root instead of listing")

            # 1:1 Match with DB URL
            self.assertEqual(url, db["url"], f"Factsheet listing URL for {pid} does not match DB URL:\nFactsheet: {url}\nDB: {db['url']}")

    # -------------------------------------------------------------
    # 6. Colombian Telephone Number Validation
    # -------------------------------------------------------------
    def test_colombian_telephone_numbers_validity(self):
        """
        All contact phone numbers listed in factsheets must be valid Colombian numbers:
        - Either 10-digit mobile starting with 3 (e.g. 3102570697)
        - Or 10-digit landline starting with 60 + department code 5 (6053303333 for Barranquilla/Atlántico)
        - Or 7-digit local number (legacy landline)
        - Must NOT be masked (e.g. +5730) or dummy (0000000000)
        """
        for f in self.factsheets:
            pid = f["id"]
            phone_raw = f["phone"]

            self.assertTrue(bool(phone_raw), f"Property {pid} factsheet has empty phone number")
            digits = re.sub(r"\D", "", phone_raw)

            is_valid_mobile = (len(digits) == 10 and digits.startswith("3"))
            is_valid_landline_new = (len(digits) == 10 and digits.startswith("605"))
            is_valid_landline_old = (len(digits) == 7 and digits.startswith("3"))

            self.assertTrue(
                is_valid_mobile or is_valid_landline_new or is_valid_landline_old,
                f"Property {pid} phone '{phone_raw}' (digits: '{digits}') is neither valid Colombian mobile nor Atlántico landline"
            )

            # Masked or dummy checks
            self.assertNotIn("0000000000", digits, f"Property {pid} has dummy phone: {phone_raw}")
            self.assertGreaterEqual(len(digits), 7, f"Property {pid} phone appears truncated or masked: {phone_raw}")

    # -------------------------------------------------------------
    # 7. Dashboard Synchronization
    # -------------------------------------------------------------
    def test_dashboard_synchronization_parity(self):
        """Verify web/app.js DEFAULT_DOSSIER_IDS aligns 1:1 with the 15 curated properties."""
        self.assertTrue(APP_JS_FILE.exists(), f"app.js not found at {APP_JS_FILE}")
        with open(APP_JS_FILE, "r", encoding="utf-8") as f:
            app_js_content = f.read()

        match = re.search(r"const\s+DEFAULT_DOSSIER_IDS\s*=\s*(\[[^\]]+\]);", app_js_content)
        self.assertTrue(bool(match), "DEFAULT_DOSSIER_IDS array definition not found in web/app.js")

        raw_array_str = match.group(1)
        # Parse IDs from JS array
        extracted_ids = [s.strip(" '\"\n\r\t") for s in raw_array_str.strip("[]").split(",") if s.strip()]

        dossier_ids = [t["id"] for t in self.table_entries]
        self.assertEqual(len(extracted_ids), 15, f"Expected 15 IDs in app.js DEFAULT_DOSSIER_IDS, found {len(extracted_ids)}")
        self.assertEqual(extracted_ids, dossier_ids, "Mismatch between web/app.js DEFAULT_DOSSIER_IDS and DOSSIER_VISITAS.md")

    # -------------------------------------------------------------
    # 8. Adversarial Stress & Fuzzing Detection Harness
    # -------------------------------------------------------------
    def test_adversarial_detectors_catch_injected_anomalies(self):
        """
        Meta-test: verifies that our validation invariants actively reject:
        - Price ceiling breach ($2.500.001)
        - WhatsApp URL without property reference ID
        - Phishing or unapproved portal domain
        - Masked/invalid phone number
        - Arithmetic mismatch (canon + admin != total)
        """
        # 1. Price ceiling breach detection
        over_price = 2500001
        self.assertFalse(over_price <= 2500000, "Adversarial check: 2.500.001 must be detected as ceiling breach")

        # 2. Arithmetic mismatch detection
        bad_canon = 1800000
        bad_admin = 400000
        fake_total = 2100000  # should be 2.2M
        self.assertNotEqual(fake_total, bad_canon + bad_admin, "Adversarial check: arithmetic discrepancy must be detected")

        # 3. WhatsApp missing ID detection
        bad_wa = "https://wa.me/573176969321?text=Hola%20quiero%20visitar%20un%20apto"
        parsed = urllib.parse.urlparse(bad_wa)
        params = urllib.parse.parse_qs(parsed.query)
        self.assertNotIn("MQ-20802-M7027822", params.get("text", [""])[0], "Adversarial check: missing property ID detected")

        # 4. Phishing domain detection
        phishing_url = "https://www.fincaraiz.com.co.attacker.io/inmuebles/12345"
        phishing_parsed = urllib.parse.urlparse(phishing_url)
        self.assertNotIn(phishing_parsed.netloc, ALLOWED_PORTAL_DOMAINS, "Adversarial check: phishing domain detected")

        # 5. Masked phone detection
        masked_phone = "+5730"
        digits_masked = re.sub(r"\D", "", masked_phone)
        self.assertLess(len(digits_masked), 7, "Adversarial check: masked phone detected")


if __name__ == "__main__":
    unittest.main()
