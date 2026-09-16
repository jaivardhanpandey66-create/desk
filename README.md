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
  `~/Documents/Desk/*.quill`, exports HTML/TXT.
- **Ledger** — 26×50 grid, formulas (`=A1+B2`, `=SUM(A1:A5)`,
  `=AVERAGE(A1:A5)`), CSV import/export, saves `*.ledger`.
- **Stage** — slide decks, fullscreen present mode (←/→), saves `*.stage`.

Double-click any `.quill` / `.ledger` / `.stage` file to open it in
DESK (registered with the OS on `./install.sh`).

## Pictures

Quill (🖼 button) and Stage (🖼 per slide) search free images via
`GET /api/images?q=...`. Pictures load through an on-server proxy
(`GET /api/img?url=...`, cached in `~/.cache/desk/img`) so hotlink-blocked
images display correctly. AI pictures via ✨ Generate (Gemini key in
`~/.config/gemini/key`, never committed).

| Source | Key needed? |
|---|---|
| Wikimedia Commons | No — built in |
| Openverse (Flickr & friends) | No — built in |
| Gemini AI generation | Yes — key file (free quota is small; enable billing for more) |
| Google Custom Search | Optional — set `GOOGLE_CSE_KEY` + `GOOGLE_CSE_CX` |
| Pinterest | Not possible — Pinterest offers no public search API |

## Zoom & updates

Header has 🔍 zoom (−/+/Ctrl+=/−/0) and ⬆ Update (pulls latest from GitHub
into the installed copy — restart after).

## Files

| File | Purpose |
|---|---|
| `desk_web.py` | stdlib server + file API (port 8400) |
| `desk_ui.html` | all three apps |
| `manifest.json` / `sw.js` | PWA installability + offline |
| `desk_app.py` | GTK desktop window |
| `desk.desktop` / `install.sh` | system install |

Sibling projects: CHIP · JARVIS · FRIDAY · STARK · CORTEX. MIT.
