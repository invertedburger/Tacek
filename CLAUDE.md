# Tácek — Claude instructions

## Project overview

Tácek is a Python scraper that fetches daily lunch menus from restaurants near Holandská, Brno. It uses Google Gemini to parse PDF and HTML menus, ranks dishes by FODMAP and fitness levels, and generates a static website (HTML files) deployed to GitHub Pages and uploaded via FTP.

**Entry point:** `run.py`  
**Config:** `config.json` (restaurant URLs, display names, parsers), `secrets.json` (API keys + FTP credentials — never commit)  
**Output:** `results/` — `index.html`, `logs.html`, `profile.html`, per-restaurant `*_results.html` and `*_data.json`

**Deployment pipeline:**
- Oracle Free Tier VM fires `deploy/trigger_github.sh` via cron at 10:37 and 11:37 Prague time (Mon–Fri)
- Trigger calls GitHub Actions `workflow_dispatch` on `invertedburger/Tacek`
- GitHub Actions runs `run.py`, deploys to GitHub Pages, FTP is handled directly in Python during the run

## Key modules

| File | Responsibility |
|---|---|
| `tacek/downloader.py` | Download PDFs, webpages, images; extract text; hashing for cache |
| `tacek/analyzer.py` | Gemini API calls — parse menus from PDF/text/image |
| `tacek/processor.py` | Orchestrates download → analyze → cache → HTML → FTP upload |
| `tacek/ranking.py` | Score and filter dishes by FODMAP + fitness; detect today's menu |
| `tacek/html/index_page.py` | Main index page (restaurant cards, map, weekend detection JS) |
| `tacek/html/menu_page.py` | Per-restaurant menu detail page |
| `tacek/ftp.py` | FTP upload — only active when `ftp_host` is set in secrets.json |
| `tacek/geocoder.py` | Geocode restaurant addresses for the map |

## Agents

### Developer agent
- Implements features, fixes bugs, refactors code
- After any change to HTML generation (`tacek/html/*.py`), always verify the output renders correctly by inspecting the generated HTML
- After changes to `ranking.py` or `analyzer.py`, run the test suite
- Never commit `secrets.json`
- Keep `config.json` as the single source of truth for restaurant configuration

### Tester agent
The tester agent verifies that code changes work correctly. Run it after any non-trivial change.

**1. Unit tests**
```bash
python -m pytest tests/ -v
```
All tests must pass. Tests cover: `ranking.py` (date parsing, dish scoring, today detection) and `html/components.py` (date parsing).

**2. HTML output check**
Generate the site locally (requires `secrets.json` with valid keys) and inspect output:
```bash
python run.py
```
Then verify `results/index.html`:
- Contains `id="cards-grid"` and `id="weekend-msg"`
- Weekend JS block present: `_dow === 0 || _dow === 6`
- Footer contains timestamp
- Each restaurant card has either a "Zobrazit celé menu" or "Menu z minulého dne" button, or a "Menu nedostupné" block

**3. Weekend behaviour**
Open `results/index.html` in a browser and check the browser console:
- On a weekday: cards grid is visible, weekend message hidden
- On a weekend: cards grid hidden, `🛋️` weekend message visible
- Can be simulated by temporarily patching `new Date().getDay()` in DevTools

**4. FTP upload check**
If `ftp_host` is set in `secrets.json`, confirm each restaurant file and `index.html` are uploaded — check `processor.py` log output for `"Uploaded to FTP:"` lines.

**5. Oracle trigger check**
```bash
~/tacek/deploy/trigger_github.sh
```
Must print `HTTP 204`. Anything else means the PAT is expired or has wrong scope (`workflow` required).

**6. Cron timing check**
On the Oracle VM:
```bash
crontab -l
grep CRON_TZ <(crontab -l)   # must show Europe/Prague
```
Confirm both entries point to `/home/ubuntu/tacek/...` (not `/home/opc/`).

## Coding conventions

- HTML is generated as f-strings in `tacek/html/*.py` — no templating engine
- All client-side logic is plain JS embedded directly in the HTML (no build step)
- Cache invalidation uses file hash (`file_hash`) and content hash (`text_hash`, `image_content_hash`)
- `log()` from `tacek/logger.py` is used throughout — do not use `print()` for operational output
- Secrets are never hardcoded — always read from `secrets.json` via `tacek/config.py`
