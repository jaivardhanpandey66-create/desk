#!/usr/bin/env python3
"""DESK desktop window (WebKitGTK, no Electron) — the 'install it' option."""
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(HERE, "desk_web.py")
PORT = 8400


def _up():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
        return True
    except Exception:
        return False


def main():
    if not _up():
        subprocess.Popen([sys.executable, SERVER_SCRIPT, "--host", "127.0.0.1",
                          "--port", str(PORT)])
        for _ in range(50):
            if _up():
                break
            time.sleep(0.2)
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import Gtk, WebKit2
    except Exception as e:
        print(f"GTK/WebKit unavailable ({e}) — use the browser at "
              f"http://127.0.0.1:{PORT}")
        return
    win = Gtk.Window(title="DESK")
    win.set_default_size(1200, 800)
    win.connect("destroy", Gtk.main_quit)
    view = WebKit2.WebView()
    uri = f"http://127.0.0.1:{PORT}/"
    # Double-clicked file from the file manager → open it in the right app
    for arg in sys.argv[1:]:
        if os.path.isfile(arg):
            import shutil
            import urllib.parse
            docs = os.path.join(os.path.expanduser("~"), "Documents", "Desk")
            os.makedirs(docs, exist_ok=True)
            dest = os.path.join(docs, os.path.basename(arg))
            if os.path.abspath(arg) != os.path.abspath(dest):
                shutil.copy(arg, dest)
            uri += "?open=" + urllib.parse.quote(os.path.basename(arg))
            break
    view.load_uri(uri)
    win.add(view)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
