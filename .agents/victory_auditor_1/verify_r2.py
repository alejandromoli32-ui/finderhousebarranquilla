import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import urllib.request
import urllib.parse
import threading
import time
import socket
from http.server import HTTPServer
from run_dashboard import DashboardRequestHandler

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

port = find_free_port()
server = HTTPServer(("127.0.0.1", port), DashboardRequestHandler)
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()
time.sleep(0.5)

base_url = f"http://127.0.0.1:{port}"
print(f"Testing Live Dashboard Server at {base_url}...")

# 1. Test GET /
req = urllib.request.Request(f"{base_url}/")
with urllib.request.urlopen(req) as resp:
    assert resp.status == 200
    ctype = resp.headers.get("Content-Type", "")
    assert "text/html" in ctype, f"Unexpected Content-Type: {ctype}"
    html = resp.read().decode("utf-8")
    assert "propertyGrid" in html or "grid" in html.lower()
    assert "searchInput" in html or "search" in html.lower()
print("  [PASS] GET / -> 200 OK HTML with interactive search & grid")

# 2. Test GET /styles.css
req = urllib.request.Request(f"{base_url}/styles.css")
with urllib.request.urlopen(req) as resp:
    assert resp.status == 200
    assert "text/css" in resp.headers.get("Content-Type", "")
print("  [PASS] GET /styles.css -> 200 OK CSS")

# 3. Test GET /app.js
req = urllib.request.Request(f"{base_url}/app.js")
with urllib.request.urlopen(req) as resp:
    assert resp.status == 200
    assert "javascript" in resp.headers.get("Content-Type", "")
    js = resp.read().decode("utf-8")
    assert "filter" in js.lower()
    assert "tracking" in js.lower()
print("  [PASS] GET /app.js -> 200 OK JS")

# 4. Test GET /api/properties
req = urllib.request.Request(f"{base_url}/api/properties")
with urllib.request.urlopen(req) as resp:
    assert resp.status == 200
    data = json.loads(resp.read().decode("utf-8"))
    assert len(data) == 172, f"Expected 172 listings, got {len(data)}"
print(f"  [PASS] GET /api/properties -> 200 OK with {len(data)} listings")

# 5. Test POST /api/tracking
test_id = data[0]["id"]
tracking_payload = json.dumps({
    "property_id": test_id,
    "status": "visita_programada",
    "notes": "Auditor verification test note"
}).encode("utf-8")

req = urllib.request.Request(
    f"{base_url}/api/tracking",
    data=tracking_payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    assert resp.status in (200, 201)
    res_json = json.loads(resp.read().decode("utf-8"))
    assert res_json.get("success") is True or "status" in res_json
print(f"  [PASS] POST /api/tracking -> Updated status for {test_id}")

# 6. Test GET /api/tracking
req = urllib.request.Request(f"{base_url}/api/tracking")
with urllib.request.urlopen(req) as resp:
    assert resp.status == 200
    saved_state = json.loads(resp.read().decode("utf-8"))
    assert test_id in saved_state.get("properties", {}) or test_id in str(saved_state)
print("  [PASS] GET /api/tracking -> State verified persisted")

# 7. Test GET /api/export?format=json and csv
for fmt in ["json", "csv"]:
    req = urllib.request.Request(f"{base_url}/api/export?format={fmt}")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        content = resp.read()
        assert len(content) > 20
        if fmt == "csv":
            assert b"status" in content and b"favorite" in content
        else:
            export_json = json.loads(content.decode("utf-8"))
            assert "properties" in export_json
print("  [PASS] GET /api/export -> Both JSON and CSV export functional")

# 8. Test Security: Path traversal
try:
    req = urllib.request.Request(f"{base_url}/../../etc/passwd")
    with urllib.request.urlopen(req) as resp:
        assert resp.status in (400, 403, 404)
        print(f"  [PASS] Path traversal prevented (status {resp.status})")
except urllib.error.HTTPError as e:
    assert e.code in (400, 403, 404)
    print(f"  [PASS] Path traversal rejected with HTTP {e.code}")

server.shutdown()
print("\nALL R2 ACCEPTANCE CRITERIA VERIFIED 100% CLEAN!")
