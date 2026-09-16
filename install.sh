#!/usr/bin/env bash
# DESK installer — the "install it" option.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/.local/share/desk"
mkdir -p "$DST" "$HOME/Documents/Desk" "$HOME/.local/share/applications" "$HOME/.local/share/mime/packages"
cp "$SRC/desk_web.py" "$SRC/desk_ui.html" "$SRC/desk_app.py" "$SRC/manifest.json" "$SRC/sw.js" "$SRC/desk.svg" "$DST/"
cp "$SRC/desk-mime.xml" "$HOME/.local/share/mime/packages/desk-mime.xml"
sed "s|%h|$HOME|g" "$SRC/desk.desktop" > "$HOME/.local/share/applications/desk.desktop"
chmod +x "$DST/desk_app.py"
# Teach the OS: .quill.html/.ledger/.stage open in DESK
update-mime-database "$HOME/.local/share/mime" >/dev/null 2>&1 || true
update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
xdg-mime default desk.desktop application/x-desk-quill application/x-desk-ledger application/x-desk-stage >/dev/null 2>&1 || true
echo "DESK installed. Launch 'DESK Office' from your app menu,"
echo "or run: python3 $DST/desk_app.py [file]"
echo "Double-click .quill.html / .ledger / .stage files to open them in DESK."
echo "Browser-only: python3 $SRC/desk_web.py  →  http://127.0.0.1:8400"
