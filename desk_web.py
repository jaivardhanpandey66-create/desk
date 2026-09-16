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
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote, quote

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HOME, "desk")  # git source (for updates)
DOCS_DIR = os.path.join(HOME, "Documents", "Desk")
CACHE_DIR = os.path.join(HOME, ".cache", "desk", "img")
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

GEM_KEY_FILE = os.path.expanduser("~/.config/gemini/key")
GEM_IMG_MODELS = ["gemini-2.5-flash-image", "gemini-3.1-flash-image",
                  "gemini-3-pro-image"]


def _gemini_key():
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if k:
        return k
    try:
        if os.path.exists(GEM_KEY_FILE):
            return open(GEM_KEY_FILE).read().strip()
    except OSError:
        pass
    return ""

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\- ]{0,80}$")


def _safe_path(name):
    name = (name or "").strip().replace("/", "").replace("\\", "")
    if not SAFE_NAME.match(name):
        return None
    return os.path.join(DOCS_DIR, name)


# ---------------------------------------------------------------------------
# Image search — pictures for Quill & Stage.
# Keyless by default (Wikimedia Commons + Openverse, both free, no signup).
# Google Custom Search plugs in when GOOGLE_CSE_KEY + GOOGLE_CSE_CX are set
# (needs a Google Cloud key — paid after the free quota). Pinterest offers no
# public search API, so it cannot be wired directly.
# ---------------------------------------------------------------------------

def _fetch_json(url, timeout=6.0):
    req = urllib.request.Request(url, headers={"User-Agent": "DESK-Office/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace") or "{}")


def image_search_wikimedia(q, n=6):
    api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
           "&generator=search&gsrsearch=" + quote(q) + "&gsrnamespace=6"
           "&gsrlimit=" + str(min(n, 20)) + "&prop=imageinfo"
           "&iiprop=url%7Csize%7Cmime&iiurlwidth=640")
    try:
        data = _fetch_json(api)
    except Exception:
        return []
    out = []
    for page in (data.get("query") or {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if url:
            out.append({"title": page.get("title", "").replace("File:", ""),
                        "url": url, "source": "wikimedia"})
    return out[:n]


def image_search_openverse(q, n=6):
    api = "https://api.openverse.org/v1/images/?q=" + quote(q) + "&page_size=" + str(min(n, 20))
    try:
        data = _fetch_json(api)
    except Exception:
        return []
    out = []
    for it in data.get("results", [])[:n]:
        if it.get("url"):
            out.append({"title": it.get("title") or q, "url": it["url"],
                        "source": "openverse",
                        "page": it.get("foreign_landing_url", "")})
    return out


def image_search_google(q, n=6):
    key, cx = os.environ.get("GOOGLE_CSE_KEY", ""), os.environ.get("GOOGLE_CSE_CX", "")
    if not (key and cx):
        return None  # not configured — caller reports google:false
    api = ("https://www.googleapis.com/customsearch/v1?key=" + quote(key)
           + "&cx=" + quote(cx) + "&searchType=image&num=" + str(min(max(n, 1), 10))
           + "&q=" + quote(q))
    try:
        data = _fetch_json(api)
    except Exception:
        return []
    return [{"title": it.get("title", q), "url": it.get("link", ""),
             "source": "google"} for it in data.get("items", []) if it.get("link")]


# ---------------------------------------------------------------------------
# Image proxy — fixes broken pictures (hotlink protection, expiring URLs).
# The server fetches the bytes once, caches them, and the UI loads them
# from DESK itself. SSRF-guarded: http(s) only, no localhost/private nets,
# 8 MB cap, must actually be an image.
# ---------------------------------------------------------------------------

import hashlib
import ipaddress
import socket

IMG_MAX_BYTES = 8 * 1024 * 1024


def _img_ok_url(url):
    try:
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            return False
        host = u.hostname.lower()
        if host in ("localhost",) or host.endswith(".localhost"):
            return False
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(host))
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except Exception:
            return False
        return True
    except Exception:
        return False


def image_proxy_fetch(url):
    if not _img_ok_url(url):
        return None, "blocked url"
    fn = hashlib.sha256(url.encode()).hexdigest()
    for ext in (".img",):
        fp = os.path.join(CACHE_DIR, fn + ext)
        if os.path.exists(fp):
            with open(fp, "rb") as f:
                head = f.read(64)
            ctype = "image/jpeg"
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                ctype = "image/png"
            elif head[:3] == b"GIF":
                ctype = "image/gif"
            elif head[:4] == b"RIFF":
                ctype = "image/webp"
            with open(fp, "rb") as f:
                return f.read(), ctype
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DESK-Office/1.0",
                                                   "Referer": "https://commons.wikimedia.org/"})
        with urllib.request.urlopen(req, timeout=15) as r:
            ctype = (r.headers.get("Content-Type", "") or "").split(";")[0].strip()
            if not ctype.startswith("image/"):
                return None, "not an image: " + ctype
            data = r.read(IMG_MAX_BYTES + 1)
            if len(data) > IMG_MAX_BYTES:
                return None, "image too large"
        with open(os.path.join(CACHE_DIR, fn + ".img"), "wb") as f:
            f.write(data)
        return data, ctype
    except Exception as e:
        return None, str(e)[:120]


def image_gemini(prompt):
    """Generate a picture with Gemini (uses ~/.config/gemini/key).
    Tries models in order — first one with quota wins."""
    import urllib.error
    key = _gemini_key()
    if not key:
        return None, "no Gemini key (set GEMINI_API_KEY or ~/.config/gemini/key)"
    body = json.dumps({
        "contents": [{"parts": [{"text": "Generate an image: " + prompt[:500]}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}).encode()
    last_err = ""
    for model in GEM_IMG_MODELS:
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               + model + ":generateContent?key=" + key)
        try:
            req = urllib.request.Request(url, data=body,
                                         headers={"Content-Type": "application/json",
                                                  "User-Agent": "DESK-Office/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read().decode() or "{}")
                msg = detail.get("error", {}).get("message", "")
            except Exception:
                msg = ""
            last_err = f"{model}: HTTP {e.code} {msg}".strip()[:200]
            if e.code == 429:  # quota — try next model
                continue
            return None, "Gemini error: " + last_err
        except Exception as e:
            last_err = f"{model}: {e}"[:200]
            continue
        try:
            for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                inline = p.get("inlineData") or {}
                if inline.get("data"):
                    mime = inline.get("mimeType", "image/png")
                    return ("data:%s;base64,%s" % (mime, inline["data"])), ""
        except Exception:
            pass
        last_err = f"{model}: no image in response"
    return None, "Gemini quota exhausted on all models — " + last_err + \
        " (enable billing on your Google Cloud project or wait for reset)"


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
        if path == "/api/images":
            qs = parse_qs(parsed.query)
            q = (qs.get("q") or [""])[0].strip()[:200]
            if not q:
                return self._json({"error": "missing q"}, 400)
            try:
                n = min(max(int((qs.get("n") or ["8"])[0]), 1), 15)
            except ValueError:
                n = 8
            results = image_search_wikimedia(q, n)
            if len(results) < n:
                results += image_search_openverse(q, n - len(results))
            google = image_search_google(q, n)
            return self._json({"query": q, "results": results,
                               "sources": {"wikimedia_openverse": len(results),
                                           "google": False if google is None else len(google),
                                           "google_results": google or []}})
        if path == "/api/img":
            qs = parse_qs(parsed.query)
            url = (qs.get("url") or [""])[0]
            if not url:
                return self._json({"error": "missing url"}, 400)
            data, ctype = image_proxy_fetch(url)
            if data is None:
                return self._json({"error": ctype}, 502)
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/version":
            import subprocess
            commit = "unknown"
            try:
                r = subprocess.run(["git", "-C", SRC_DIR, "rev-parse", "--short", "HEAD"],
                                   capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    commit = r.stdout.strip()
            except Exception:
                pass
            return self._json({"version": commit, "gemini": bool(_gemini_key())})
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
        if self.path == "/api/generate":
            prompt = (data.get("prompt") or "").strip()
            if not prompt:
                return self._json({"error": "empty prompt"}, 400)
            img, err = image_gemini(prompt)
            if img is None:
                return self._json({"error": err}, 502)
            return self._json({"ok": True, "image": img})
        if self.path == "/api/update":
            import shutil
            import subprocess
            log = []
            try:
                r = subprocess.run(["git", "-C", SRC_DIR, "pull", "--ff-only"],
                                   capture_output=True, text=True, timeout=60)
                log.append((r.stdout + r.stderr).strip()[:500] or "already up to date")
                if r.returncode == 0:
                    for fn in ("desk_web.py", "desk_ui.html", "desk_app.py",
                               "manifest.json", "sw.js", "desk.svg"):
                        src, dst = os.path.join(SRC_DIR, fn), os.path.join(HERE, fn)
                        if os.path.abspath(src) != os.path.abspath(dst) and os.path.exists(src):
                            shutil.copy(src, dst)
                    log.append("installed copy refreshed — restart the app")
                else:
                    log.append("pull failed")
            except Exception as e:
                log.append("update error: " + str(e)[:200])
            return self._json({"ok": True, "log": log})
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
