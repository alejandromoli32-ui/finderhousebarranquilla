"""
Adversarial Stress Test Suite for Milestone 2: Backend Server & State Persistence API.
Authored by challenger_m2_1.

Empirical verification of:
1. High-concurrency POST /api/tracking calls from 20 parallel threads (no corruption, no dropped keys).
2. Malformed payloads: invalid JSON strings, non-dictionary bodies, invalid UTF-8 bytes (HTTP 400 without crashing).
3. Port contention: bind port 8000 and verify fallback to port 8001+ smoothly.
"""

import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

# Ensure root directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from run_dashboard import (
    TRACKING_FILE,
    create_server,
    find_free_port,
)


class TestAdversarialM2Server(unittest.TestCase):
    """Empirical adversarial test suite for run_dashboard.py."""

    @classmethod
    def setUpClass(cls):
        os.environ["DASHBOARD_QUIET"] = "1"
        # Isolate tracking store in a temporary directory so production data is never mutated
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.isolated_tracking_path = Path(cls.temp_dir.name) / "test_adv_user_tracking.json"
        os.environ["TRACKING_STORE_PATH"] = str(cls.isolated_tracking_path)

        # Initialize test server on high port
        cls.start_port = find_free_port(start_port=9400)
        cls.server, cls.actual_port = create_server(host="127.0.0.1", port=cls.start_port)
        cls.base_url = f"http://127.0.0.1:{cls.actual_port}"

        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.shutdown()
            cls.server.server_close()
        except Exception:
            pass
        os.environ.pop("TRACKING_STORE_PATH", None)
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def _post_raw(self, path: str, raw_data: bytes, content_type: str = "application/json"):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(
            url,
            data=raw_data,
            headers={"Content-Type": content_type}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def _get(self, path: str):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    # =========================================================================
    # 1. HIGH-CONCURRENCY STRESS TESTS (20 Parallel Threads)
    # =========================================================================

    def test_concurrency_20_threads_no_dropped_keys(self):
        """20 parallel threads concurrently POSTing tracking updates must not drop any keys."""
        thread_count = 20
        requests_per_thread = 5  # Total 100 distinct properties
        all_expected_ids = set()
        errors = []
        barrier = threading.Barrier(thread_count)

        def worker(t_idx):
            barrier.wait()  # Maximize concurrent race conditions
            for r_idx in range(requests_per_thread):
                pid = f"ADV-CONCUR-T{t_idx:02d}-R{r_idx:02d}"
                all_expected_ids.add(pid)
                payload = {
                    "property_id": pid,
                    "status": "favorito" if (t_idx + r_idx) % 3 == 0 else "visita_programada",
                    "favorite": (t_idx % 2 == 0),
                    "notes": f"Stress test note from thread {t_idx} request {r_idx}",
                    "rating": (r_idx % 5) + 1
                }
                body = json.dumps(payload).encode("utf-8")
                status, _, _ = self._post_raw("/api/tracking", body)
                if status != 200:
                    errors.append(f"Thread {t_idx} req {r_idx} failed with HTTP {status}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Encountered errors during concurrent POSTs: {errors}")

        # Verify disk file is valid JSON and not corrupt
        self.assertTrue(TRACKING_FILE.exists())
        with open(TRACKING_FILE, "r", encoding="utf-8") as f:
            disk_data = json.load(f)

        self.assertIsInstance(disk_data, dict)
        disk_props = disk_data.get("properties", {})

        # Verify 100% of expected keys are present (zero dropped keys)
        missing_keys = all_expected_ids - set(disk_props.keys())
        self.assertEqual(
            len(missing_keys), 0,
            f"Concurrency failure: {len(missing_keys)} keys dropped: {list(missing_keys)[:10]}"
        )

        # Verify GET endpoint returns all keys
        status, _, content = self._get("/api/tracking")
        self.assertEqual(status, 200)
        api_data = json.loads(content.decode("utf-8"))
        api_props = api_data.get("properties", {})
        self.assertTrue(all_expected_ids.issubset(set(api_props.keys())))

    def test_concurrency_race_condition_updates_same_key(self):
        """Multiple threads concurrently updating the EXACT same property ID."""
        target_pid = "ADV-SHARED-HOT-KEY"
        thread_count = 20
        barrier = threading.Barrier(thread_count)
        errors = []

        def worker(idx):
            barrier.wait()
            payload = {
                "property_id": target_pid,
                "status": "visita_programada",
                "favorite": True,
                "notes": f"Update from thread {idx}",
                "rating": (idx % 5) + 1
            }
            body = json.dumps(payload).encode("utf-8")
            status, _, _ = self._post_raw("/api/tracking", body)
            if status != 200:
                errors.append(f"Worker {idx} got HTTP {status}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])

        with open(TRACKING_FILE, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        self.assertIn(target_pid, disk_data["properties"])
        self.assertEqual(disk_data["properties"][target_pid]["status"], "visita_programada")
        self.assertIn(target_pid, disk_data["visits"])

    def test_concurrency_mixed_read_write_stress(self):
        """20 threads performing mixed rapid reads (GET) and writes (POST)."""
        thread_count = 20
        barrier = threading.Barrier(thread_count)
        errors = []

        def worker(idx):
            barrier.wait()
            if idx % 2 == 0:
                pid = f"ADV-MIXED-RW-{idx}"
                payload = {"property_id": pid, "status": "favorito", "favorite": True}
                status, _, _ = self._post_raw("/api/tracking", json.dumps(payload).encode("utf-8"))
                if status != 200:
                    errors.append(f"Writer {idx} failed with {status}")
            else:
                status, _, content = self._get("/api/tracking")
                if status != 200:
                    errors.append(f"Reader {idx} failed with {status}")
                else:
                    try:
                        parsed = json.loads(content.decode("utf-8"))
                        if "properties" not in parsed:
                            errors.append(f"Reader {idx} got invalid structure")
                    except Exception as e:
                        errors.append(f"Reader {idx} JSON decode failed: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])

    # =========================================================================
    # 2. MALFORMED PAYLOADS & ERROR HANDLING TESTS
    # =========================================================================

    def test_malformed_invalid_json_syntax(self):
        """Invalid JSON syntax must return HTTP 400 without crashing the server."""
        bad_json_samples = [
            b'{"unclosed": true,',
            b'}{',
            b'<<<NOT_JSON>>>',
            b"{'single_quotes': 'invalid_in_json'}",
            b'{"key": undefined}',
            b'{"val": [1, 2, 3, ]}',
        ]
        for sample in bad_json_samples:
            status, _, body = self._post_raw("/api/tracking", sample)
            self.assertEqual(
                status, 400,
                f"Payload {sample} produced status {status} instead of 400. Body: {body}"
            )

        # Confirm server remains alive
        alive_status, _, _ = self._get("/")
        self.assertEqual(alive_status, 200)

    def test_malformed_non_dictionary_bodies(self):
        """Valid JSON but non-dictionary root (int, string, list, bool, null) must return HTTP 400."""
        non_dict_samples = [
            (b"12345", "integer"),
            (b'"just a string"', "string"),
            (b"[1, 2, 3]", "array"),
            (b"true", "boolean"),
            (b"null", "null"),
            (b"3.14159", "float"),
            (b"NaN", "nan"),
        ]
        for raw, label in non_dict_samples:
            status, _, body = self._post_raw("/api/tracking", raw)
            self.assertEqual(
                status, 400,
                f"Non-dictionary body ({label}: {raw}) produced status {status} instead of 400. Body: {body}"
            )

        alive_status, _, _ = self._get("/")
        self.assertEqual(alive_status, 200)

    def test_malformed_invalid_utf8_bytes(self):
        """Invalid UTF-8 byte sequences must return HTTP 400 without crashing the server."""
        bad_utf8_samples = [
            b"\xff\xfe\xfa\x00",
            b"\x80\x81\x82\x83",
            b"\xc0\xaf",
        ]
        for sample in bad_utf8_samples:
            status, _, body = self._post_raw("/api/tracking", sample)
            self.assertEqual(
                status, 400,
                f"Invalid UTF-8 sample {sample} produced status {status} instead of 400. Body: {body}"
            )

        alive_status, _, _ = self._get("/")
        self.assertEqual(alive_status, 200)

    def test_empty_payload(self):
        """Empty payload (Content-Length 0) must return HTTP 400."""
        status, _, _ = self._post_raw("/api/tracking", b"")
        self.assertEqual(status, 400)

    # =========================================================================
    # 3. PORT CONTENTION & DYNAMIC FALLBACK TESTS
    # =========================================================================

    def test_port_contention_port_8000_fallback(self):
        """Binding port 8000 with a standard socket causes create_server(port=8000) to fall back to 8001+."""
        # Standard socket on port 8000
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bound = False
        try:
            sock.bind(("127.0.0.1", 8000))
            sock.listen(1)
            bound = True
        except OSError:
            sock.close()

        if not bound:
            self.skipTest("Port 8000 is occupied by an external service")

        try:
            fallback_server, actual_port = create_server(host="127.0.0.1", port=8000, max_attempts=10)
            self.assertGreater(actual_port, 8000, f"Port was not incremented from 8000: got {actual_port}")
            self.assertIn(actual_port, range(8001, 8011))

            # Verify server is fully operational on fallback port
            fb_thread = threading.Thread(target=fallback_server.serve_forever, daemon=True)
            fb_thread.start()
            time.sleep(0.1)

            req = urllib.request.Request(f"http://127.0.0.1:{actual_port}/")
            with urllib.request.urlopen(req, timeout=5) as res:
                self.assertEqual(res.status, 200)

            fallback_server.shutdown()
            fallback_server.server_close()
        finally:
            sock.close()

    def test_port_contention_consecutive_occupied_ports(self):
        """When multiple consecutive ports are occupied by standard sockets, fallback finds the next free port."""
        start = find_free_port(start_port=9600)
        socks = []
        for p in range(start, start + 3):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", p))
            s.listen(1)
            socks.append(s)

        try:
            server, chosen_port = create_server(host="127.0.0.1", port=start, max_attempts=10)
            self.assertEqual(chosen_port, start + 3)
            server.server_close()
        finally:
            for s in socks:
                s.close()

    def test_port_contention_dual_dashboard_windows_collision(self):
        """
        Vulnerability verification: When an existing ReusableThreadingServer instance is on port 8000,
        does create_server(port=8000) detect the collision or collide due to SO_REUSEADDR on Windows?
        """
        srv1, p1 = create_server(host="127.0.0.1", port=8000)
        srv2 = None
        try:
            srv2, p2 = create_server(host="127.0.0.1", port=8000)
            # Both servers should NOT bind to the exact same port
            self.assertNotEqual(
                p1, p2,
                f"Vulnerability detected: Both servers bound to {p1}! "
                f"allow_reuse_address=True on Windows allows socket hijacking instead of falling back."
            )
        finally:
            srv1.server_close()
            if srv2:
                srv2.server_close()


if __name__ == "__main__":
    unittest.main()
