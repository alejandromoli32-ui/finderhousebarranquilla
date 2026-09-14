#!/usr/bin/env python3
"""
Tracker de Apartamentos y Casas en Arriendo - Barranquilla Norte
Local Web Dashboard Server & State Persistence Engine.

Zero external dependencies - Python 3.12 Standard Library only.
Serves the web Single Page Application and provides REST API for state tracking.
"""

import argparse
from datetime import datetime, timezone
import http.server
import json
import mimetypes
import os
from pathlib import Path
import socket
import sys
import threading
import urllib.parse
import webbrowser

# Ensure Windows standard streams handle UTF-8 without crashing
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = (BASE_DIR / "web").resolve()
DATA_DIR = (BASE_DIR / "data").resolve()
PROPERTIES_FILE = DATA_DIR / "inmuebles_barranquilla.json"
CSV_FILE = DATA_DIR / "inmuebles_barranquilla.csv"

_CUSTOM_TRACKING_PATH = None


def get_tracking_file_path() -> Path:
    """Returns the current path for user_tracking.json, supporting environment override."""
    global _CUSTOM_TRACKING_PATH
    if _CUSTOM_TRACKING_PATH is not None:
        return _CUSTOM_TRACKING_PATH
    env_path = os.environ.get("TRACKING_STORE_PATH") or os.environ.get("TRACKING_FILE")
    if env_path:
        return Path(env_path).resolve()
    return (DATA_DIR / "user_tracking.json").resolve()


def set_tracking_file_path(path: Path | str | None) -> None:
    """Configures an in-memory override for the tracking file path."""
    global _CUSTOM_TRACKING_PATH
    if path is None:
        _CUSTOM_TRACKING_PATH = None
    else:
        _CUSTOM_TRACKING_PATH = Path(path).resolve()


class _TrackingFileProxy(os.PathLike):
    """Proxy object so TRACKING_FILE always resolves dynamically to active store path."""

    def __fspath__(self):
        return str(get_tracking_file_path())

    def __str__(self):
        return str(get_tracking_file_path())

    def __repr__(self):
        return repr(get_tracking_file_path())

    def __getattr__(self, name):
        return getattr(get_tracking_file_path(), name)

    def __truediv__(self, other):
        return get_tracking_file_path() / other


TRACKING_FILE = _TrackingFileProxy()

_TRACKING_LOCK = threading.RLock()


def get_default_tracking() -> dict:
    """Returns an empty, valid user tracking structure."""
    return {
        "version": "1.0",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "properties": {},
        "favorites": [],
        "visits": [],
        "discarded": [],
        "notes": {}
    }


def load_tracking_data() -> dict:
    """Thread-safe read of user tracking data from disk."""
    with _TRACKING_LOCK:
        if not TRACKING_FILE.exists():
            default_data = get_default_tracking()
            save_tracking_data_locked(default_data)
            return default_data
        try:
            with open(TRACKING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = get_default_tracking()
                # Ensure all required root keys exist
                data.setdefault("version", "1.0")
                data.setdefault("last_updated", datetime.now(timezone.utc).isoformat())
                data.setdefault("properties", {})
                data.setdefault("favorites", [])
                data.setdefault("visits", [])
                data.setdefault("discarded", [])
                data.setdefault("notes", {})
                return data
        except Exception:
            return get_default_tracking()


def save_tracking_data_locked(data: dict) -> None:
    """Atomic write of user tracking data to disk (must hold _TRACKING_LOCK)."""
    target_path = get_tracking_file_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target_path.with_suffix(".json.tmp")
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Atomic replace
    os.replace(temp_file, target_path)


def update_tracking_state(payload: dict) -> dict:
    """Thread-safe update and synchronization of tracking state."""
    if not isinstance(payload, dict):
        raise TypeError("Payload must be a dictionary")
    with _TRACKING_LOCK:
        current = load_tracking_data()
        properties = current.setdefault("properties", {})

        if "property_id" in payload:
            pid = str(payload["property_id"]).strip()
            existing = properties.get(pid, {})
            new_status = payload.get("status", existing.get("status", "sin_gestionar"))
            is_fav = payload.get("favorite", existing.get("favorite", False))
            if new_status == "favorito":
                is_fav = True

            record = {
                "status": new_status,
                "favorite": bool(is_fav),
                "visit_date": payload.get("visit_date", existing.get("visit_date")),
                "notes": payload.get("notes", existing.get("notes", "")),
                "rating": payload.get("rating", existing.get("rating", 0)),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            properties[pid] = record

        elif "properties" in payload and isinstance(payload["properties"], dict):
            for pid, pdata in payload["properties"].items():
                if isinstance(pdata, dict):
                    properties[str(pid).strip()] = pdata

        # Sync convenience list collections
        current["favorites"] = [
            pid for pid, d in properties.items()
            if d.get("favorite") or d.get("status") == "favorito"
        ]
        current["visits"] = [
            pid for pid, d in properties.items()
            if d.get("status") == "visita_programada"
        ]
        current["discarded"] = [
            pid for pid, d in properties.items()
            if d.get("status") == "descartado"
        ]
        current["notes"] = {
            pid: d.get("notes", "")
            for pid, d in properties.items()
            if d.get("notes")
        }

        save_tracking_data_locked(current)
        return current


class DashboardRequestHandler(http.server.BaseHTTPRequestHandler):
    """Custom HTTP request handler serving SPA static files and REST API endpoints."""

    def log_message(self, format, *args):
        # Suppress verbose standard logging during automated tests
        if os.environ.get("DASHBOARD_QUIET"):
            return
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}\n")

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # API: Properties JSON
        if path in ("/api/properties", "/data/inmuebles_barranquilla.json"):
            if not PROPERTIES_FILE.exists():
                self.send_error(404, "Properties dataset not found")
                return
            try:
                with open(PROPERTIES_FILE, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self._set_cors_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, f"Error reading properties: {e}")
            return

        # API: Properties CSV
        if path == "/data/inmuebles_barranquilla.csv":
            if not CSV_FILE.exists():
                self.send_error(404, "Properties CSV not found")
                return
            try:
                with open(CSV_FILE, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self._set_cors_headers()
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, f"Error reading CSV: {e}")
            return

        # API: User Tracking GET
        if path == "/api/tracking":
            try:
                tracking = load_tracking_data()
                body = json.dumps(tracking, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(200)
                self._set_cors_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_error(500, f"Error reading tracking: {e}")
            return

        # API: Export
        if path == "/api/export":
            query = urllib.parse.parse_qs(parsed.query)
            fmt = query.get("format", ["json"])[0].lower()
            tracking = load_tracking_data()
            if fmt == "csv":
                rows = ["id,status,favorite,visit_date,rating,notes\n"]
                for pid, d in tracking.get("properties", {}).items():
                    notes_clean = d.get("notes", "").replace('"', '""')
                    rows.append(
                        f'"{pid}","{d.get("status","")}","{d.get("favorite",False)}",'
                        f'"{d.get("visit_date","")}","{d.get("rating",0)}","{notes_clean}"\n'
                    )
                content = "".join(rows).encode("utf-8-sig")
                self.send_response(200)
                self._set_cors_headers()
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", "attachment; filename=user_tracking.csv")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                body = json.dumps(tracking, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(200)
                self._set_cors_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", "attachment; filename=user_tracking.json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        # Static file routing - strictly restricted to WEB_DIR
        clean_rel = path.lstrip("/")
        if clean_rel in ("", "index.html"):
            target_rel = "index.html"
        elif clean_rel in ("styles.css", "web/styles.css"):
            target_rel = "styles.css"
        elif clean_rel in ("app.js", "web/app.js"):
            target_rel = "app.js"
        elif clean_rel.startswith("web/"):
            target_rel = clean_rel[4:].lstrip("/")
        else:
            target_rel = clean_rel

        # Prevent directory traversal attacks and enforce WEB_DIR boundary
        try:
            resolved_target = (WEB_DIR / target_rel).resolve()
            if not resolved_target.is_relative_to(WEB_DIR):
                self.send_error(403, "Access forbidden")
                return
        except (ValueError, RuntimeError):
            self.send_error(403, "Access forbidden")
            return

        if not resolved_target.exists():
            self.send_error(404, f"File not found: {path}")
            return
        if not resolved_target.is_file():
            self.send_error(403, "Access forbidden")
            return

        if resolved_target.suffix == ".js":
            mime_type = "application/javascript"
        elif resolved_target.suffix == ".css":
            mime_type = "text/css"
        elif resolved_target.suffix == ".svg":
            mime_type = "image/svg+xml"
        else:
            mime_type, _ = mimetypes.guess_type(str(resolved_target))
            if not mime_type:
                mime_type = "application/octet-stream"

        if mime_type.startswith("text/") or mime_type in ("application/javascript", "application/json"):
            content_type = f"{mime_type}; charset=utf-8"
        else:
            content_type = mime_type

        try:
            with open(resolved_target, "rb") as f:
                content = f.read()
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

    def _send_json_error(self, code: int, error_msg: str):
        """Helper to send structured JSON error responses."""
        self.send_response(code)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        body = json.dumps({"error": error_msg, "code": code}).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/tracking":
            try:
                try:
                    content_length = int(self.headers.get("Content-Length", 0))
                except (ValueError, TypeError):
                    self._send_json_error(400, "Invalid Content-Length header")
                    return

                if content_length <= 0:
                    self._send_json_error(400, "Empty payload")
                    return

                raw_body = self.rfile.read(content_length)

                try:
                    decoded_body = raw_body.decode("utf-8")
                except (UnicodeDecodeError, Exception):
                    self._send_json_error(400, "Invalid UTF-8 payload")
                    return

                try:
                    payload = json.loads(decoded_body)
                except (json.JSONDecodeError, ValueError):
                    self._send_json_error(400, "Invalid JSON in request body")
                    return

                if not isinstance(payload, dict):
                    self._send_json_error(400, "Payload must be a JSON object")
                    return

                try:
                    updated = update_tracking_state(payload)
                except Exception as e:
                    self._send_json_error(400, f"Error processing tracking update: {e}")
                    return

                response_data = {
                    "success": True,
                    "timestamp": updated.get("last_updated"),
                    "data": updated
                }
                body = json.dumps(response_data, ensure_ascii=False).encode("utf-8")

                self.send_response(200)
                self._set_cors_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self._send_json_error(500, f"Internal server error: {e}")
            return

        self.send_error(404, "Endpoint not found")


class ReusableThreadingServer(http.server.ThreadingHTTPServer):
    """Threading HTTP server with Windows-safe port reuse and socket binding."""
    daemon_threads = True
    if sys.platform == "win32":
        allow_reuse_address = False
    else:
        allow_reuse_address = True

    def server_bind(self):
        if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            except OSError:
                pass
        super().server_bind()


def find_free_port(start_port: int = 8000, max_attempts: int = 50) -> int:
    """Finds an available TCP port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                except OSError:
                    pass
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_attempts}")


def create_server(host: str = "127.0.0.1", port: int = 8000, max_attempts: int = 50):
    """Creates a ThreadingHTTPServer instance, automatically finding a free port if occupied."""
    if port == 0:
        server = ReusableThreadingServer((host, 0), DashboardRequestHandler)
        actual_port = server.server_address[1]
        return server, actual_port

    last_err = None
    for p in range(port, port + max_attempts):
        try:
            server = ReusableThreadingServer((host, p), DashboardRequestHandler)
            actual_port = server.server_address[1]
            return server, actual_port
        except OSError as e:
            last_err = e
            continue
    raise RuntimeError(f"Failed to bind server on {host}:{port} ({last_err})")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Tracker Inmobiliario Barranquilla - Servidor Web Local"
    )
    parser.add_argument("--port", type=int, default=8000, help="Puerto TCP inicial (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host IP (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="No abrir automaticamente el navegador")
    args = parser.parse_args()

    server, actual_port = create_server(host=args.host, port=args.port)
    url = f"http://localhost:{actual_port}/"

    print("=" * 70, flush=True)
    print("  [TRACKER] TRACKER DE APARTAMENTOS Y CASAS EN ARRIENDO - BARRANQUILLA NORTE", flush=True)
    print("  Presupuesto maximo: $2.500.000 COP (Canon + Administracion)", flush=True)
    print("=" * 70, flush=True)
    print(f"  [PORT] Dashboard activo en:  {url}", flush=True)
    print(f"  [OK]   API de inmuebles:     http://localhost:{actual_port}/api/properties", flush=True)
    print(f"  [OK]   API de persistencia:  http://localhost:{actual_port}/api/tracking", flush=True)
    print("  [INFO] Presiona Ctrl+C para detener el servidor", flush=True)
    print("=" * 70, flush=True)

    if not args.no_browser:
        def _open_browser():
            import time
            time.sleep(0.5)
            try:
                print(f"  [BROWSER] Abriendo navegador en {url}...", flush=True)
                webbrowser.open(url)
            except Exception:
                pass
        threading.Thread(target=_open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Cerrando servidor...", flush=True)
    finally:
        server.server_close()
        print("[OK] Servidor detenido correctamente.", flush=True)


if __name__ == "__main__":
    main()
