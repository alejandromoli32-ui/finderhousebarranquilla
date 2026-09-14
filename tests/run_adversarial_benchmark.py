"""
Adversarial Benchmark & Empirical Diagnostics for Milestone 2 Server.
Authored by challenger_m2_1.
"""

import json
import os
from pathlib import Path
import shutil
import socket
import sys
import threading
import time
import urllib.error
import urllib.request

from run_dashboard import (
    TRACKING_FILE,
    create_server,
    find_free_port,
)


def run_benchmark():
    os.environ["DASHBOARD_QUIET"] = "1"
    report = {
        "concurrency": {},
        "malformed_payloads": {},
        "port_contention": {}
    }

    # Backup tracking file
    backup_path = None
    if TRACKING_FILE.exists():
        backup_path = TRACKING_FILE.with_suffix(".json.bak_bench")
        shutil.copyfile(TRACKING_FILE, backup_path)

    # Launch server
    start_port = find_free_port(start_port=9300)
    server, actual_port = create_server(host="127.0.0.1", port=start_port)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.2)
    base_url = f"http://127.0.0.1:{actual_port}"

    def do_post(body: bytes, content_type: str = "application/json"):
        req = urllib.request.Request(
            f"{base_url}/api/tracking",
            data=body,
            headers={"Content-Type": content_type}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, res.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as ex:
            return -1, str(ex)

    def do_get(path: str):
        req = urllib.request.Request(f"{base_url}{path}")
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, res.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as ex:
            return -1, str(ex)

    print("--- 1. Testing Malformed Payloads ---")
    payload_matrix = [
        ("invalid_json_syntax", b'{"bad_json": ', 400),
        ("invalid_json_unquoted", b'{test: 123}', 400),
        ("invalid_json_nan", b'NaN', 400),
        ("non_dict_int", b'12345', 400),
        ("non_dict_string", b'"hello string"', 400),
        ("non_dict_array", b'[1, 2, 3]', 400),
        ("non_dict_bool", b'true', 400),
        ("non_dict_null", b'null', 400),
        ("invalid_utf8_ff", b'\xff\xfe\xfa\x00', 400),
        ("invalid_utf8_80", b'\x80\x81\x82', 400),
        ("empty_payload", b'', 400),
    ]

    for name, raw_bytes, expected_status in payload_matrix:
        status, response_text = do_post(raw_bytes)
        alive_status, _ = do_get("/")
        server_alive = (alive_status == 200)
        passed = (status == expected_status and server_alive)
        report["malformed_payloads"][name] = {
            "status_code": status,
            "expected_status": expected_status,
            "server_alive": server_alive,
            "passed": passed,
            "response_snippet": response_text[:120].strip()
        }
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}: got HTTP {status} (expected {expected_status}), alive={server_alive}")

    print("\n--- 2. Testing High Concurrency (20 Threads) ---")
    thread_count = 20
    reqs_per_thread = 5
    barrier = threading.Barrier(thread_count)
    concurrency_errors = []
    expected_keys = set()
    start_time = time.time()

    def worker(t_idx):
        barrier.wait()
        for r_idx in range(reqs_per_thread):
            pid = f"BENCH-T{t_idx:02d}-R{r_idx:02d}"
            expected_keys.add(pid)
            body = json.dumps({
                "property_id": pid,
                "status": "favorito" if (t_idx + r_idx) % 2 == 0 else "visita_programada",
                "favorite": True,
                "notes": f"Concurrency test t={t_idx} r={r_idx}"
            }).encode("utf-8")
            status, resp = do_post(body)
            if status != 200:
                concurrency_errors.append(f"Worker {t_idx} req {r_idx} failed with {status}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duration = time.time() - start_time

    # Inspect disk
    with open(TRACKING_FILE, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    disk_props = disk_data.get("properties", {})
    missing = expected_keys - set(disk_props.keys())

    report["concurrency"] = {
        "threads": thread_count,
        "total_requests": thread_count * reqs_per_thread,
        "duration_seconds": round(duration, 3),
        "errors": concurrency_errors,
        "total_keys_expected": len(expected_keys),
        "total_keys_persisted": len(disk_props),
        "missing_keys_count": len(missing),
        "passed": (len(concurrency_errors) == 0 and len(missing) == 0)
    }
    print(f"  [{'PASS' if report['concurrency']['passed'] else 'FAIL'}] Concurrency: {len(expected_keys)} keys expected, {len(disk_props)} keys in file, missing={len(missing)}, errors={len(concurrency_errors)}")

    # Clean up test server
    server.shutdown()
    server.server_close()

    print("\n--- 3. Testing Port Contention & Fallback ---")
    # Case 3.1: Standard socket on port 8000
    s8000 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bound_8000 = False
    try:
        s8000.bind(("127.0.0.1", 8000))
        s8000.listen(1)
        bound_8000 = True
    except OSError:
        pass

    if bound_8000:
        srv_fb, p_fb = create_server(host="127.0.0.1", port=8000)
        report["port_contention"]["standard_socket_port_8000"] = {
            "requested_port": 8000,
            "actual_bound_port": p_fb,
            "fallback_successful": (p_fb > 8000)
        }
        print(f"  [{'PASS' if p_fb > 8000 else 'FAIL'}] Bound socket on 8000 -> create_server bound to {p_fb}")
        srv_fb.server_close()
        s8000.close()
    else:
        report["port_contention"]["standard_socket_port_8000"] = {
            "note": "Port 8000 was already bound by system"
        }

    # Case 3.2: ReusableThreadingServer instance already running on port 8000
    srv1, p1 = create_server(host="127.0.0.1", port=8000)
    srv2, p2 = create_server(host="127.0.0.1", port=8000)
    report["port_contention"]["two_instances_reusable_server"] = {
        "server1_port": p1,
        "server2_port": p2,
        "conflict_detected": (p1 != p2),
        "explanation": "On Windows, allow_reuse_address=True permits socket hijacking/port collision instead of raising WSAEADDRINUSE"
    }
    print(f"  [{'PASS' if p1 != p2 else 'FAIL'}] Two dashboard instances requesting 8000: Server1={p1}, Server2={p2} (p1 != p2: {p1 != p2})")
    srv1.server_close()
    srv2.server_close()

    # Restore backup
    if backup_path and backup_path.exists():
        shutil.copyfile(backup_path, TRACKING_FILE)
        backup_path.unlink(missing_ok=True)

    print("\n--- Summary Report ---")
    print(json.dumps(report, indent=2))

    with open("data/adversarial_benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    run_benchmark()
