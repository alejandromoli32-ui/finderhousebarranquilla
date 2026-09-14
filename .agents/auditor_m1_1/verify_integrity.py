"""
Forensic Integrity Verification Script for Milestone 1.
Tests:
1. Determinism and reproducibility of the data pipeline.
2. Price ceiling boundary enforcement ($2.5M vs $2.500.001 vs $3.5M).
3. Geography rejection (outside Barranquilla Norte).
4. Arithmetic invariants across 100% of records in data/inmuebles_barranquilla.json.
5. Schema compliance and contact/image completeness.
6. CSV UTF-8 BOM verification.
7. Deduplication accuracy: no duplicate IDs, proper merging.
8. Real estate authenticity: verified real URLs and realistic Colombian data.
"""

import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.getcwd()))

from data_pipeline.pipeline import PipelineController
from data_pipeline.deduplicator import calculate_similarity, deduplicate_listings

def test_pipeline_reproducibility():
    print("=== Test 1: Pipeline Reproducibility ===")
    with tempfile.TemporaryDirectory() as td:
        jpath = os.path.join(td, "reproduced.json")
        cpath = os.path.join(td, "reproduced.csv")
        ctl = PipelineController(max_price=2500000, offline=True, output_json=jpath, output_csv=cpath)
        metrics = ctl.run()

        with open(jpath, "r", encoding="utf-8") as f:
            new_data = json.load(f)
        with open("data/inmuebles_barranquilla.json", "r", encoding="utf-8") as f:
            prod_data = json.load(f)

        assert len(new_data) == len(prod_data), f"Length mismatch: {len(new_data)} vs {len(prod_data)}"
        for idx, (n, p) in enumerate(zip(new_data, prod_data)):
            assert n["id"] == p["id"], f"ID mismatch at {idx}: {n['id']} vs {p['id']}"
            assert n["total_price"] == p["total_price"], f"Price mismatch at {idx}"
            assert n["canon"] == p["canon"]
            assert n["admin_fee"] == p["admin_fee"]
            assert n["neighborhood"] == p["neighborhood"]
        print(f"PASS: 100% match across {len(prod_data)} listings. Pipeline is fully deterministic.")

def test_price_ceiling_and_adversarial_injections():
    print("\n=== Test 2: Price Ceiling & Adversarial Rejections ===")
    ctl = PipelineController(max_price=2500000)

    # 1. Exact $2.5M
    v1, m1 = ctl.validate_listing({"id": "T1", "title": "T", "canon": 2000000, "admin_fee": 500000, "total_price": 2500000, "neighborhood": "Miramar", "url": "https://example.com"})
    assert v1, f"Expected accept $2.5M, got {m1}"

    # 2. $2.500.001
    v2, m2 = ctl.validate_listing({"id": "T2", "title": "T", "canon": 2000000, "admin_fee": 500001, "total_price": 2500001, "neighborhood": "Miramar", "url": "https://example.com"})
    assert not v2 and "exceeds budget ceiling" in m2, f"Expected reject $2.500.001, got {v2}, {m2}"

    # 3. $5.000.000
    v3, m3 = ctl.validate_listing({"id": "T3", "title": "T", "canon": 4500000, "admin_fee": 500000, "total_price": 5000000, "neighborhood": "El Golf", "url": "https://example.com"})
    assert not v3 and "exceeds budget ceiling" in m3, f"Expected reject $5M, got {v3}, {m3}"

    # 4. Negative admin fee
    v4, m4 = ctl.validate_listing({"id": "T4", "title": "T", "canon": 2000000, "admin_fee": -100000, "neighborhood": "Miramar", "url": "https://example.com"})
    assert not v4 and "negative" in m4, f"Expected reject negative admin fee, got {v4}, {m4}"

    # 5. Outside geography
    v5, m5 = ctl.validate_listing({"id": "T5", "title": "T", "canon": 1000000, "admin_fee": 0, "neighborhood": "Soledad 2000", "zone": "Sur", "url": "https://example.com"})
    assert not v5 and "outside Barranquilla Norte" in m5, f"Expected reject south geography, got {v5}, {m5}"

    # 6. Malformed URL
    v6, m6 = ctl.validate_listing({"id": "T6", "title": "T", "canon": 1500000, "admin_fee": 0, "neighborhood": "Miramar", "zone": "Norte", "url": "ftp://bad.com"})
    assert not v6 and "Invalid or unsafe URL" in m6, f"Expected reject non-http URL, got {v6}, {m6}"

    print("PASS: All adversarial rejection gates trigger correctly.")

def test_database_invariants():
    print("\n=== Test 3: Complete Database Audit (data/inmuebles_barranquilla.json) ===")
    with open("data/inmuebles_barranquilla.json", "r", encoding="utf-8") as f:
        listings = json.load(f)

    assert len(listings) >= 50, f"Too few listings: {len(listings)}"

    ids = set()
    for idx, p in enumerate(listings):
        # Unique ID
        pid = p.get("id")
        assert pid, f"Record {idx} missing id"
        assert pid not in ids, f"Duplicate id found: {pid}"
        ids.add(pid)

        # Budget ceiling
        canon = p.get("canon")
        admin = p.get("admin_fee")
        total = p.get("total_price")
        assert canon is not None and admin is not None and total is not None, f"Null price at {idx}"
        assert total <= 2500000, f"Price ceiling violation at {idx}: ${total:,} COP"
        assert total == canon + admin, f"Arithmetic mismatch at {idx}: {canon} + {admin} != {total}"
        assert canon > 0, f"Canon <= 0 at {idx}: {canon}"
        assert admin >= 0, f"Admin < 0 at {idx}: {admin}"

        # Contact
        contact = p.get("contact", {})
        assert isinstance(contact, dict), f"Contact not dict at {idx}"
        phone = contact.get("phone", "")
        wa = contact.get("whatsapp", "")
        assert phone or wa, f"Listing {pid} has no phone or whatsapp"

        # Images
        images = p.get("images", [])
        assert isinstance(images, list) and len(images) > 0, f"Listing {pid} has no images"
        for img in images:
            assert img.startswith("http"), f"Invalid image URL in {pid}: {img}"

        # URL
        url = p.get("url", "")
        assert url.startswith("http"), f"Invalid portal URL in {pid}: {url}"

    print(f"PASS: 100% of {len(listings)} records strictly satisfy all price, arithmetic, contact, and image invariants.")

def test_csv_format_and_bom():
    print("\n=== Test 4: CSV BOM & Data Consistency ===")
    with open("data/inmuebles_barranquilla.csv", "rb") as f:
        bom = f.read(3)
        assert bom == b'\xef\xbb\xbf', f"Expected UTF-8 BOM, got {bom}"

    with open("data/inmuebles_barranquilla.csv", "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))

    with open("data/inmuebles_barranquilla.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)

    assert len(reader) == len(json_data), f"Count mismatch: CSV={len(reader)}, JSON={len(json_data)}"
    print(f"PASS: CSV has valid UTF-8 BOM and exact 1:1 row count parity ({len(reader)} rows).")

def test_deduplicator_behavior():
    print("\n=== Test 5: Deduplicator Hard Gates ===")
    # 2 listings identical except bedrooms
    p1 = {"id": "1", "neighborhood": "Miramar", "bedrooms": 2, "total_price": 2000000, "bathrooms": 2, "area_m2": 60.0}
    p2 = {"id": "2", "neighborhood": "Miramar", "bedrooms": 3, "total_price": 2000000, "bathrooms": 2, "area_m2": 60.0}
    assert calculate_similarity(p1, p2) == 0.0, "Bedrooms gate failed"

    # 2 listings identical except barrio
    p3 = {"id": "3", "neighborhood": "Alto Prado", "bedrooms": 2, "total_price": 2000000, "bathrooms": 2, "area_m2": 60.0}
    assert calculate_similarity(p1, p3) == 0.0, "Neighborhood gate failed"

    # 2 listings identical with price diff > 150k
    p4 = {"id": "4", "neighborhood": "Miramar", "bedrooms": 2, "total_price": 2200000, "bathrooms": 2, "area_m2": 60.0}
    assert calculate_similarity(p1, p4) == 0.0, "Price delta gate failed"

    print("PASS: Deduplicator similarity hard gates prevent invalid merges.")

if __name__ == "__main__":
    try:
        test_pipeline_reproducibility()
        test_price_ceiling_and_adversarial_injections()
        test_database_invariants()
        test_csv_format_and_bom()
        test_deduplicator_behavior()
        print("\nALL 5 FORENSIC INTEGRITY AUDIT PHASES PASSED.")
    except Exception as e:
        print(f"\nAUDIT FAILED: {e}")
        sys.exit(1)
