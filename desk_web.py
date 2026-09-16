#!/usr/bin/env python3
"""
DESK — holographic office suite (Quill · Ledger · Stage).

Run in browser:
    python3 desk_web.py                 # → http://127.0.0.1:8400

Or install as an app:
    ./install.sh                        # desktop entry + optional GTK window

Zero dependencies — Python standard library only. Files live in ~/Documents/Desk.
Installable as a PWA (manifest + service worker) or via the GTK wrapper.
"""

import argparse
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(HOME, "Documents", "Desk")
os.makedirs(DOCS_DIR, exist_ok=True)

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\- ]{0,80}$")


def _safe_path(name):
    name = (name or "").strip().replace("/", "").replace("\\", "")
    if not SAFE_NAME.match(name):
        return None
    return os.path.join(DOCS_DIR, name)


MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript",
        ".json": "application/json", ".css": "text/css",
        ".svg": "image/svg+xml", ".png": "image/png"}


class Handler(BaseHTTPRequestHandler):
    server_version = "Desk/1.0"

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            self._json({"error": "not found"}, 404)
            return
        ext = os.path.splitext(path)[1].lower()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/desk_ui.html", "/index.html"):
            return self._file(os.path.join(HERE, "desk_ui.html"))
        if path in ("/manifest.json", "/sw.js", "/desk.svg"):
            return self._file(os.path.join(HERE, path.lstrip("/")))
        if path == "/api/files":
            files = sorted(f for f in os.listdir(DOCS_DIR)
                           if os.path.isfile(os.path.join(DOCS_DIR, f)))
            return self._json({"dir": DOCS_DIR, "files": files})
        if path == "/api/open":
            qs = parse_qs(parsed.query)
            name = unquote((qs.get("name") or [""])[0])
            fp = _safe_path(name)
            if not fp or not os.path.exists(fp):
                return self._json({"error": "bad name"}, 400)
            with open(fp, "r", errors="replace") as f:
                return self._json({"name": name, "content": f.read()})
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._json({"error": "bad json"}, 400)
        if self.path == "/api/save":
            name = (data.get("name") or "").strip()
            fp = _safe_path(name)
            if not fp:
                return self._json({"error": "bad name"}, 400)
            with open(fp, "w") as f:
                f.write(data.get("content", ""))
            return self._json({"ok": True, "name": name})
        if self.path == "/api/delete":
            fp = _safe_path((data.get("name") or "").strip())
            if not fp or not os.path.exists(fp):
                return self._json({"error": "bad name"}, 400)
            os.remove(fp)
            return self._json({"ok": True})
        return self._json({"error": "not found"}, 404)


def main():
    ap = argparse.ArgumentParser(description="DESK office suite")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8400)
    args = ap.parse_args()
    if args.host == "0.0.0.0":
        print("WARNING: binding to 0.0.0.0 exposes DESK to your LAN with no auth.")
    print(f"\n  DESK 1.0 — Quill · Ledger · Stage  (files: {DOCS_DIR})")
    print(f"  → http://{args.host}:{args.port}\n  Ctrl+C to stop\n")
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
