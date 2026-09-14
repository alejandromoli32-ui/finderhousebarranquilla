"""
Unit and Integration Tests for Local Web Dashboard & State Persistence Engine.
Validates HTTP Server, Static Assets Delivery, REST API endpoints, and File System Persistence.
"""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from run_dashboard import (
    BASE_DIR,
    DATA_DIR,
    PROPERTIES_FILE,
    TRACKING_FILE,
    WEB_DIR,
    create_server,
    find_free_port,
    load_tracking_data,
    update_tracking_state,
)


class TestDashboardServer(unittest.TestCase):
    """Test suite for run_dashboard.py HTTP server and API endpoints."""

    @classmethod
    def setUpClass(cls):
        # Set quiet mode for cleaner test output
        os.environ["DASHBOARD_QUIET"] = "1"

        # Isolate tracking store in a temporary directory so production data is never touched
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.isolated_tracking_path = Path(cls.temp_dir.name) / "test_user_tracking.json"
        os.environ["TRACKING_STORE_PATH"] = str(cls.isolated_tracking_path)

        # Initialize clean test server
        cls.test_port = find_free_port(start_port=8900)
        cls.server, cls.actual_port = create_server(host="127.0.0.1", port=cls.test_port)
        cls.base_url = f"http://127.0.0.1:{cls.actual_port}"

        # Run server in background daemon thread
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

        # Allow server thread to initialize socket
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        # Shutdown and close server
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

    def _http_get(self, path: str):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def _http_post_json(self, path: str, data: dict):
        url = f"{self.base_url}{path}"
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    # -------------------------------------------------------------------------
    # Static Assets Delivery Tests
    # -------------------------------------------------------------------------

    def test_root_index_html_delivery(self):
        """GET / must return 200 OK, text/html content-type and page title."""
        status, headers, content = self._http_get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        text = content.decode("utf-8")
        self.assertIn("Tracker de Arriendos", text)
        self.assertIn("Barranquilla Norte", text)
        self.assertIn("app.js", text)
        self.assertIn("styles.css", text)

    def test_index_html_direct_path(self):
        """GET /index.html must also serve index.html."""
        status, headers, content = self._http_get("/index.html")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn("Tracker de Arriendos", content.decode("utf-8"))

    def test_css_delivery(self):
        """GET /styles.css and /web/styles.css must return 200 with text/css."""
        for path in ("/styles.css", "/web/styles.css"):
            status, headers, content = self._http_get(path)
            self.assertEqual(status, 200, f"Failed on path: {path}")
            self.assertIn("text/css", headers.get("Content-Type", ""))
            css_text = content.decode("utf-8")
            self.assertIn("--teal-600", css_text)
            self.assertIn("--slate-900", css_text)
            self.assertIn("property-card", css_text)

    def test_javascript_delivery(self):
        """GET /app.js and /web/app.js must return 200 with application/javascript."""
        for path in ("/app.js", "/web/app.js"):
            status, headers, content = self._http_get(path)
            self.assertEqual(status, 200, f"Failed on path: {path}")
            self.assertIn("javascript", headers.get("Content-Type", "").lower())
            js_text = content.decode("utf-8")
            self.assertIn("applyFilters", js_text)
            self.assertIn("normalizeText", js_text)
            self.assertIn("updatePropertyTracking", js_text)

    def test_assets_delivery(self):
        """SVG assets in /assets/ must be delivered with image/svg+xml."""
        status, headers, content = self._http_get("/assets/placeholder.svg")
        self.assertEqual(status, 200)
        self.assertIn("image/svg+xml", headers.get("Content-Type", ""))
        self.assertIn("<svg", content.decode("utf-8"))

        status_logo, headers_logo, content_logo = self._http_get("/assets/logo.svg")
        self.assertEqual(status_logo, 200)
        self.assertIn("image/svg+xml", headers_logo.get("Content-Type", ""))
        self.assertIn("<svg", content_logo.decode("utf-8"))

    # -------------------------------------------------------------------------
    # Properties Catalog Delivery Tests
    # -------------------------------------------------------------------------

    def test_api_properties_json_delivery(self):
        """GET /api/properties must return the 172 verified properties."""
        status, headers, content = self._http_get("/api/properties")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        data = json.loads(content.decode("utf-8"))
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 172)

        # Check sample item structure
        sample = data[0]
        self.assertIn("id", sample)
        self.assertIn("title", sample)
        self.assertIn("total_price", sample)
        self.assertIn("neighborhood", sample)
        self.assertLessEqual(sample["total_price"], 2500000)

    def test_data_properties_json_alias(self):
        """GET /data/inmuebles_barranquilla.json must return identical catalogue."""
        status, headers, content = self._http_get("/data/inmuebles_barranquilla.json")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        data = json.loads(content.decode("utf-8"))
        self.assertEqual(len(data), 172)

    def test_data_properties_csv_delivery(self):
        """GET /data/inmuebles_barranquilla.csv must return CSV file with UTF-8 BOM."""
        status, headers, content = self._http_get("/data/inmuebles_barranquilla.csv")
        self.assertEqual(status, 200)
        self.assertIn("text/csv", headers.get("Content-Type", ""))
        self.assertGreater(len(content), 1000)

    # -------------------------------------------------------------------------
    # User Tracking & State Persistence REST API Tests
    # -------------------------------------------------------------------------

    def test_get_tracking_initial(self):
        """GET /api/tracking must return a valid tracking structure."""
        status, headers, content = self._http_get("/api/tracking")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        data = json.loads(content.decode("utf-8"))
        self.assertIn("properties", data)
        self.assertIn("favorites", data)
        self.assertIn("visits", data)
        self.assertIn("discarded", data)
        self.assertIn("notes", data)

    def test_post_tracking_single_property_persistence(self):
        """POST /api/tracking must update memory, disk file, and GET endpoint atomically."""
        test_id = "FR-TEST-PERSIST-001"
        payload = {
            "property_id": test_id,
            "status": "visita_programada",
            "favorite": True,
            "visit_date": "2026-09-18T14:30:00",
            "notes": "Visita agendada con Martha. Piden póliza de arrendamiento.",
            "rating": 5
        }

        # 1. Post tracking state
        status, headers, content = self._http_post_json("/api/tracking", payload)
        self.assertEqual(status, 200)
        res_data = json.loads(content.decode("utf-8"))
        self.assertTrue(res_data.get("success"))
        self.assertIn(test_id, res_data["data"]["properties"])

        # 2. Verify via GET /api/tracking
        get_status, _, get_content = self._http_get("/api/tracking")
        self.assertEqual(get_status, 200)
        tracking = json.loads(get_content.decode("utf-8"))
        self.assertIn(test_id, tracking["properties"])
        self.assertEqual(tracking["properties"][test_id]["status"], "visita_programada")
        self.assertEqual(tracking["properties"][test_id]["notes"], "Visita agendada con Martha. Piden póliza de arrendamiento.")
        self.assertIn(test_id, tracking["visits"])
        self.assertIn(test_id, tracking["favorites"])

        # 3. Direct verification of disk file (atomic write inspection)
        self.assertTrue(TRACKING_FILE.exists())
        with open(TRACKING_FILE, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        self.assertIn(test_id, disk_data["properties"])
        self.assertEqual(disk_data["properties"][test_id]["status"], "visita_programada")

    def test_post_tracking_discard_persistence(self):
        """POST /api/tracking with status 'descartado' must sync discarded list."""
        test_id = "FR-TEST-DISCARD-002"
        payload = {
            "property_id": test_id,
            "status": "descartado",
            "favorite": False,
            "notes": "Sin ascensor, piso 5."
        }

        status, _, content = self._http_post_json("/api/tracking", payload)
        self.assertEqual(status, 200)

        tracking = json.loads(content.decode("utf-8"))["data"]
        self.assertIn(test_id, tracking["discarded"])
        self.assertNotIn(test_id, tracking["favorites"])

    def test_concurrent_tracking_updates(self):
        """Concurrent POSTs from multiple threads must execute without corruption or deadlocks."""
        thread_count = 10
        errors = []

        def worker(idx):
            payload = {
                "property_id": f"CONCURRENT-PROP-{idx}",
                "status": "favorito" if idx % 2 == 0 else "visita_programada",
                "favorite": True,
                "notes": f"Concurrent test note from thread {idx}"
            }
            status, _, _ = self._http_post_json("/api/tracking", payload)
            if status != 200:
                errors.append(f"Thread {idx} got status {status}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        status, _, content = self._http_get("/api/tracking")
        self.assertEqual(status, 200)
        data = json.loads(content.decode("utf-8"))
        for i in range(thread_count):
            pid = f"CONCURRENT-PROP-{i}"
            self.assertIn(pid, data["properties"])

    def test_post_tracking_invalid_json(self):
        """POST /api/tracking with invalid JSON must return 400 Bad Request."""
        url = f"{self.base_url}/api/tracking"
        req = urllib.request.Request(
            url,
            data=b"INVALID_NOT_JSON",
            headers={"Content-Type": "application/json"}
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)

    # -------------------------------------------------------------------------
    # Export Endpoint Tests
    # -------------------------------------------------------------------------

    def test_export_json_and_csv(self):
        """GET /api/export must return downloadable JSON or CSV attachments."""
        # JSON export
        status_j, headers_j, content_j = self._http_get("/api/export?format=json")
        self.assertEqual(status_j, 200)
        self.assertIn("application/json", headers_j.get("Content-Type", ""))
        self.assertIn("attachment", headers_j.get("Content-Disposition", ""))

        # CSV export
        status_c, headers_c, content_c = self._http_get("/api/export?format=csv")
        self.assertEqual(status_c, 200)
        self.assertIn("text/csv", headers_c.get("Content-Type", ""))
        self.assertIn("attachment", headers_c.get("Content-Disposition", ""))

    # -------------------------------------------------------------------------
    # Dynamic Port Handling & Security Boundary Tests
    # -------------------------------------------------------------------------

    def test_dynamic_port_conflict_resolution(self):
        """If a port is already in use, create_server should bind to port+1."""
        # Occupy actual_port + 10 with a dummy socket
        conflict_port = find_free_port(start_port=self.actual_port + 10)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", conflict_port))
        sock.listen(1)

        try:
            # create_server starting at conflict_port must auto-increment to conflict_port + 1
            alt_server, bound_port = create_server(host="127.0.0.1", port=conflict_port, max_attempts=5)
            self.assertNotEqual(bound_port, conflict_port)
            self.assertGreater(bound_port, conflict_port)
            alt_server.server_close()
        finally:
            sock.close()

    def test_path_traversal_protection(self):
        """Attempting path traversal must be rejected with 403 or 404."""
        status, _, _ = self._http_get("/../../secret.txt")
        self.assertIn(status, (400, 403, 404))

        status_etc, _, _ = self._http_get("/..%2f..%2fetc%2fpasswd")
        self.assertIn(status_etc, (400, 403, 404))

    def test_windows_console_startup_cp1252_zero_crash(self):
        """Invoking python run_dashboard.py under cp1252 encoding must start without UnicodeEncodeError."""
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "cp1252"
        env["PYTHONUTF8"] = "0"
        env["DASHBOARD_QUIET"] = "0"

        # 1. Test CLI help execution
        res_help = subprocess.run(
            [sys.executable, "-u", str(BASE_DIR / "run_dashboard.py"), "--help"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        self.assertEqual(res_help.returncode, 0)
        self.assertNotIn("UnicodeEncodeError", res_help.stderr)

        # 2. Test actual invocation with --no-browser --port 0
        proc = subprocess.Popen(
            [sys.executable, "-u", str(BASE_DIR / "run_dashboard.py"), "--no-browser", "--port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        try:
            time.sleep(1.2)
            self.assertIsNone(proc.poll(), "Server process terminated prematurely")
        finally:
            proc.terminate()
            try:
                stdout_tail, stderr_tail = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout_tail, stderr_tail = proc.communicate()

        self.assertIn("[TRACKER]", stdout_tail)
        self.assertNotIn("UnicodeEncodeError", stderr_tail)

    def test_post_tracking_invalid_utf8_payload(self):
        """POST /api/tracking with invalid UTF-8 bytes must return 400 with 'Invalid UTF-8 payload'."""
        url = f"{self.base_url}/api/tracking"
        req = urllib.request.Request(
            url,
            data=b"\xff\xfe\xfa\x00",
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read().decode("utf-8")
        self.assertEqual(status, 400)
        self.assertIn("Invalid UTF-8 payload", body)

    def test_post_tracking_non_dict_payload(self):
        """POST /api/tracking with non-dict JSON body must return 400 with 'Payload must be a JSON object'."""
        for non_dict in (b"12345", b'"simple string"', b"[1, 2, 3]", b"true", b"null"):
            url = f"{self.base_url}/api/tracking"
            req = urllib.request.Request(
                url,
                data=non_dict,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    status = resp.status
                    body = resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                status = e.code
                body = e.read().decode("utf-8")
            self.assertEqual(status, 400, f"Non-dict payload {non_dict} returned {status}")
            self.assertIn("Payload must be a JSON object", body)

    def test_static_file_serving_restrictions(self):
        """Static file serving must restrict access to web/ and refuse internal project files."""
        # Internal Python source code must not be served
        status_src, _, _ = self._http_get("/run_dashboard.py")
        self.assertIn(status_src, (403, 404))

        # Batch script must not be served
        status_bat, _, _ = self._http_get("/start_dashboard.bat")
        self.assertIn(status_bat, (403, 404))

        # Internal agent metadata must not be served
        status_agent, _, _ = self._http_get("/.agents/orchestrator_1/PROJECT.md")
        self.assertIn(status_agent, (403, 404))

        # User tracking file directly via static route must not be served
        status_track, _, _ = self._http_get("/data/user_tracking.json")
        self.assertIn(status_track, (403, 404))


if __name__ == "__main__":
    unittest.main()
