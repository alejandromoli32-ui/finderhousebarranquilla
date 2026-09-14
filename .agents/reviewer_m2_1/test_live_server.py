import subprocess
import time
import urllib.request
import json
import os
import sys

def run_test():
    print("Starting run_dashboard.py on port 8889...")
    proc = subprocess.Popen(
        [sys.executable, "run_dashboard.py", "--port", "8889", "--no-browser"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to print the active URL
    ready = False
    for _ in range(20):
        time.sleep(0.3)
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            print("Process died unexpectedly!")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return
        try:
            with urllib.request.urlopen("http://127.0.0.1:8889/", timeout=1) as res:
                if res.status == 200:
                    ready = True
                    break
        except Exception:
            pass
            
    if not ready:
        print("Server did not become ready in time.")
        stdout, stderr = proc.communicate()
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return

    try:
        # 1. Test GET /
        with urllib.request.urlopen("http://127.0.0.1:8889/", timeout=5) as res:
            assert res.status == 200
            html = res.read().decode('utf-8')
            assert "<!DOCTYPE html>" in html
            assert "Tracker de Arriendos" in html
            print("GET / -> 200 OK (verified HTML contents)")

        # 2. Test GET /styles.css
        with urllib.request.urlopen("http://127.0.0.1:8889/styles.css", timeout=5) as res:
            assert res.status == 200
            css = res.read().decode('utf-8')
            assert "--slate-900" in css
            assert "--teal-600" in css
            print("GET /styles.css -> 200 OK (verified CSS variables)")

        # 3. Test GET /app.js
        with urllib.request.urlopen("http://127.0.0.1:8889/app.js", timeout=5) as res:
            assert res.status == 200
            js = res.read().decode('utf-8')
            assert "applyFilters" in js
            assert "normalizeText" in js
            print("GET /app.js -> 200 OK (verified JS code)")

        # 4. Test GET /api/properties
        with urllib.request.urlopen("http://127.0.0.1:8889/api/properties", timeout=5) as res:
            assert res.status == 200
            props = json.loads(res.read().decode('utf-8'))
            assert isinstance(props, list)
            assert len(props) == 172
            print(f"GET /api/properties -> 200 OK (172 properties delivered)")

        # 5. Test POST /api/tracking
        post_data = {
            "property_id": "REVIEWER-TEST-001",
            "status": "favorito",
            "notes": "Reviewed and verified live.",
            "rating": 5
        }
        req = urllib.request.Request(
            "http://127.0.0.1:8889/api/tracking",
            data=json.dumps(post_data).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            assert res.status == 200
            resp = json.loads(res.read().decode('utf-8'))
            assert resp["success"] is True
            assert "REVIEWER-TEST-001" in resp["data"]["properties"]
            print("POST /api/tracking -> 200 OK (tracked property successfully)")

        # 6. Test GET /api/tracking
        with urllib.request.urlopen("http://127.0.0.1:8889/api/tracking", timeout=5) as res:
            assert res.status == 200
            tracking = json.loads(res.read().decode('utf-8'))
            assert "REVIEWER-TEST-001" in tracking["properties"]
            assert "REVIEWER-TEST-001" in tracking["favorites"]
            print("GET /api/tracking -> 200 OK (state confirmed in tracking store)")

        print("ALL LIVE SERVER INTEGRATION CHECKS PASSED!")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
        print("Server stopped cleanly.")

if __name__ == "__main__":
    run_test()
