#!/usr/bin/env bash
# DESK installer — the "install it" option.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/.local/share/desk"
mkdir -p "$DST" "$HOME/Documents/Desk" "$HOME/.local/share/applications"
cp "$SRC/desk_web.py" "$SRC/desk_ui.html" "$SRC/desk_app.py" "$SRC/manifest.json" "$SRC/sw.js" "$SRC/desk.svg" "$DST/"
sed "s|%h|$HOME|g" "$SRC/desk.desktop" > "$HOME/.local/share/applications/desk.desktop"
chmod +x "$DST/desk_app.py"
echo "DESK installed. Launch 'DESK Office' from your app menu,"
echo "or run: python3 $DST/desk_app.py"
echo "Browser-only: python3 $SRC/desk_web.py  →  http://127.0.0.1:8400"
