"""
Adversarial stress test script for run_dashboard.py
Run from reviewer_m2_2 to stress-test HTTP server, API endpoints, persistence, and security boundaries.
"""

import http.client
import json
import socket
import sys
import threading
import time
import urllib.request
import urllib.error

from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from run_dashboard import create_server, find_free_port, load_tracking_data, update_tracking_state

def test_adversarial_suite():
    print("=== Starting Adversarial Stress Test Suite ===")
    
    # 1. Start server on an ephemeral port
    port = find_free_port(start_port=9200)
    server, actual_port = create_server(host="127.0.0.1", port=port)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.2)
    base_url = f"http://127.0.0.1:{actual_port}"
    print(f"Server started on {base_url}")
    
    results = {}

    # Test A: POST /api/tracking with non-dict JSON (null, integer, list)
    for bad_payload, desc in [(None, "null"), (12345, "number"), ([1, 2, 3], "list"), ("hello", "string")]:
        try:
            req = urllib.request.Request(
                f"{base_url}/api/tracking",
                data=json.dumps(bad_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                status = resp.status
                body = resp.read()
                results[f"POST non-dict JSON ({desc})"] = f"Status {status}"
        except urllib.error.HTTPError as e:
            results[f"POST non-dict JSON ({desc})"] = f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"
        except Exception as ex:
            results[f"POST non-dict JSON ({desc})"] = f"Error: {ex}"

    # Test B: File disclosure / traversal in BASE_DIR
    for test_path, desc in [
        ("/run_dashboard.py", "Root python file"),
        ("/.agents/orchestrator_1/PROJECT.md", "Agent internal metadata"),
        ("/web/../run_dashboard.py", "Dot-dot within base dir"),
        ("/web/app.js", "Legitimate web app asset"),
        ("/../../windows/win.ini", "Escape base dir to OS root")
    ]:
        try:
            req = urllib.request.Request(f"{base_url}{test_path}")
            with urllib.request.urlopen(req, timeout=3) as resp:
                status = resp.status
                results[f"Disclosure test ({desc}) {test_path}"] = f"HTTP {status} (Length: {len(resp.read())})"
        except urllib.error.HTTPError as e:
            results[f"Disclosure test ({desc}) {test_path}"] = f"HTTP {e.code}"
        except Exception as ex:
            results[f"Disclosure test ({desc}) {test_path}"] = f"Error: {ex}"

    # Test C: Heavy Concurrent Load (50 threads spamming POST /api/tracking simultaneously)
    print("Running high-concurrency stress test (50 threads)...")
    concurrent_errors = []
    def heavy_worker(t_id):
        try:
            payload = {
                "property_id": f"STRESS-{t_id}",
                "status": "favorito" if t_id % 2 == 0 else "descartado",
                "notes": f"Stress note from thread {t_id}" * 10,
                "rating": t_id % 5 + 1
            }
            req = urllib.request.Request(
                f"{base_url}/api/tracking",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status != 200:
                    concurrent_errors.append(f"Thread {t_id} got status {resp.status}")
        except Exception as e:
            concurrent_errors.append(f"Thread {t_id} failed: {e}")

    threads = [threading.Thread(target=heavy_worker, args=(i,)) for i in range(50)]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    t1 = time.time()
    results["50-thread concurrency"] = f"Completed in {t1 - t0:.2f}s, errors: {len(concurrent_errors)}"

    # Test D: Malformed Content-Length header
    try:
        conn = http.client.HTTPConnection("127.0.0.1", actual_port, timeout=3)
        conn.putrequest("POST", "/api/tracking")
        conn.putheader("Content-Length", "not_a_number")
        conn.endheaders()
        resp = conn.getresponse()
        results["Malformed Content-Length"] = f"HTTP {resp.status}"
        conn.close()
    except Exception as ex:
        results["Malformed Content-Length"] = f"Error: {ex}"

    # Test E: Empty POST body with Content-Length 0
    try:
        conn = http.client.HTTPConnection("127.0.0.1", actual_port, timeout=3)
        conn.putrequest("POST", "/api/tracking")
        conn.putheader("Content-Length", "0")
        conn.endheaders()
        resp = conn.getresponse()
        results["POST Content-Length 0"] = f"HTTP {resp.status}"
        conn.close()
    except Exception as ex:
        results["POST Content-Length 0"] = f"Error: {ex}"

    # Test F: GET /api/export format parameter fuzzing
    for fmt in ["csv", "json", "XML", "'; DROP TABLE;--", ""]:
        try:
            req = urllib.request.Request(f"{base_url}/api/export?format={urllib.parse.quote(fmt)}")
            with urllib.request.urlopen(req, timeout=3) as resp:
                results[f"Export format fuzz '{fmt}'"] = f"HTTP {resp.status}, Content-Type: {resp.headers.get('Content-Type')}"
        except Exception as ex:
            results[f"Export format fuzz '{fmt}'"] = f"Error: {ex}"

    # Test G: Port exhaustion test
    try:
        # Request a port range where no ports are available
        # Find an open port, bind to it, and request 1 max_attempt
        dummy_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dummy_port = find_free_port(start_port=9300)
        dummy_s.bind(("127.0.0.1", dummy_port))
        dummy_s.listen(1)
        try:
            create_server(host="127.0.0.1", port=dummy_port, max_attempts=1)
            results["Port exhaustion exception"] = "FAILED: Did not raise RuntimeError"
        except RuntimeError as re:
            results["Port exhaustion exception"] = f"PASSED: Raised {type(re).__name__}"
        finally:
            dummy_s.close()
    except Exception as ex:
        results["Port exhaustion exception"] = f"Error: {ex}"

    # Shutdown server
    server.shutdown()
    server.server_close()
    
    print("\n=== Results Summary ===")
    for k, v in results.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    test_adversarial_suite()
