# DESK — Holographic Office Suite

**Quill** (documents) · **Ledger** (spreadsheets) · **Stage** (presentations).
Zero dependencies. Pure Python standard library + one HTML file.

## Two ways to run

| Option | Command |
|---|---|
| **Browser** | `python3 desk_web.py` → http://127.0.0.1:8400 |
| **Installed app** | `./install.sh`, then launch **DESK Office** (GTK window, no Electron) |
| **Phone/tablet** | Open the URL, browser offers **Install** (PWA) |

## Apps

- **Quill** — rich text (bold/italic/lists/headings), word count, saves to
  `~/Documents/Desk/*.quill.html`, exports HTML/TXT.
- **Ledger** — 26×50 grid, formulas (`=A1+B2`, `=SUM(A1:A5)`,
  `=AVERAGE(A1:A5)`), CSV import/export, saves JSON.
- **Stage** — slide decks, fullscreen present mode (←/→), saves JSON.

## Files

| File | Purpose |
|---|---|
| `desk_web.py` | stdlib server + file API (port 8400) |
| `desk_ui.html` | all three apps |
| `manifest.json` / `sw.js` | PWA installability + offline |
| `desk_app.py` | GTK desktop window |
| `desk.desktop` / `install.sh` | system install |

Sibling projects: CHIP · JARVIS · FRIDAY · STARK · CORTEX. MIT.
