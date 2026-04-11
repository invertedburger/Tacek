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

## Directory structure

```text
Tacek/
├── run.py                      # Entry point — orchestrates the full run
├── config.json                 # Restaurant config (URLs, names, parsers) — commit this
├── secrets.json                # API keys + FTP credentials — NEVER commit
├── requirements.txt
│
├── tacek/                      # Main package
│   ├── config.py               # Loads config.json + secrets.json, exports all constants
│   ├── downloader.py           # HTTP download (PDF, page, image), text extraction, hashing
│   ├── analyzer.py             # AI parsing: Groq (primary) → Gemini (fallback)
│   ├── processor.py            # Pipeline: download → analyze → cache → HTML → FTP
│   ├── ranking.py              # Dish scoring (FODMAP + fitness) and today-detection
│   ├── ftp.py                  # FTP upload (no-ops if ftp_host is empty)
│   ├── geocoder.py             # Geocode restaurant addresses for map markers
│   ├── logger.py               # Structured run logger; log() writes to run_log.json
│   └── html/
│       ├── index_page.py       # index.html — restaurant cards, map, weekend JS
│       ├── menu_page.py        # *_results.html — per-restaurant dish detail page
│       ├── profile_page.py     # profile.html — dietary preferences UI
│       ├── logs_page.py        # logs.html — run history viewer
│       ├── components.py       # Shared HTML helpers (badges, date parsing)
│       └── assets.py           # Inline CSS (chip styles) and theme toggle JS
│
├── tests/
│   ├── test_ranking.py         # Unit tests for ranking.py (scoring, date detection)
│   └── test_components.py      # Unit tests for html/components.py (date parsing)
│
├── deploy/
│   ├── trigger_github.sh       # Calls GitHub API to fire workflow_dispatch
│   ├── setup_oracle.sh         # One-time Oracle VM setup script
│   └── crontab.txt             # Crontab to install on Oracle VM
│
├── menus/                      # Downloaded PDFs and images (gitignored)
├── results/                    # Generated HTML + JSON output (gitignored)
│
└── .github/workflows/
    └── build.yml               # GitHub Actions: runs run.py, deploys to Pages
```

## Data flow

```text
config.json + secrets.json
        │
        ▼
   processor.py
        │
        ├─ PDF URL ──► downloader.download_file() ──► menus/*.pdf
        │                                                   │
        │                                           analyzer.analyze_pdf()
        │                                           (Gemini file API → image render → text)
        │
        ├─ Webpage (text) ──► downloader.download_webpage()
        │                     downloader.extract_menu_text()
        │                                   │
        │                           analyzer.analyze_text()
        │                           (Groq llama-3.3-70b → Gemini fallback)
        │
        └─ Webpage (image) ──► downloader.find_menu_images()
                               downloader.download_image()
                                           │
                                   analyzer.analyze_image()
                                   (Groq llama-4-scout vision → Gemini fallback)
                                           │
                                           ▼
                                  results/*_data.json   ◄── cached by hash
                                           │
                          ┌────────────────┤
                          │                │
                   ranking.py         html/menu_page.py
                   (top dishes)            │
                          │                ▼
                          └──► html/index_page.py ──► results/index.html
                                                           │
                                                       ftp.upload()
```

## Restaurants and parser types

| Restaurant | Domain | Parser |
| --- | --- | --- |
| IQ Restaurant | `www.iqrestaurant.cz` | `pdf` — downloads menu.pdf |
| Il Paladar | `www.ilpaladar.cz` | `auto` (text extraction) |
| U Tesaře | `www.utesare.cz` | `image` — menu posted as image |
| U Hovězího Pupku | `www.uhovezihopupku.cz` | `auto` (text extraction) |
| Kometa Pub | `www.kometapub.cz` | `auto` (text extraction) |
| Buddha 2 | `www.menicka.cz` | `auto` (text extraction via menicka iframe) |

Parser is set per-domain in `config.json` under `webpage_parsers`. Default is `auto`, which falls back to image parsing if extracted text is shorter than `min_menu_text_length` (200 chars).

## AI analysis pipeline

**Text and webpage menus:**

1. Groq (`llama-3.3-70b-versatile`) — fast, free tier
2. Gemini (`gemini-2.5-flash-lite`) — fallback if Groq fails or returns empty days

**Image menus (U Tesaře):**

1. Groq vision (`llama-4-scout-17b-16e-instruct`) — image downscaled to 1024px wide
2. Gemini — fallback

**PDF menus (IQ Restaurant):**

1. Gemini file API (PDF uploaded directly) — best quality
2. Render each page to PNG → image pipeline above
3. PyMuPDF text extraction → text pipeline above

All paths return the same JSON schema:
```json
{
  "days": [
    {
      "day": "Pondělí 14.4.2026",
      "dishes": [
        {
          "name": "Svíčková na smetaně",
          "fodmap_level": "High",
          "fitness_level": "Medium",
          "problematic_ingredients": ["gluten", "onion"],
          "protein_g": 35,
          "carbs_g": 60,
          "fat_g": 20,
          "calories_kcal": 560
        }
      ]
    }
  ]
}
```

## Caching strategy

Processor checks a hash before re-analyzing:

- **PDFs:** SHA-256 of the file bytes (`file_hash`) → stored in `results/processed_files.log`
- **Text pages:** SHA-256 of extracted text (`text_hash`) → stored in `results/processed_webpages.log`
- **Image pages:** SHA-256 of downloaded image bytes (`image_content_hash`) → same log

Cache hit skips the AI call and regenerates HTML from the existing `*_data.json`. Cache is invalidated automatically when the restaurant updates their menu (file/content changes).

## Dish ranking

`ranking.get_top_dishes(data, n=3)` returns up to 3 best dishes for today:

- Filters to today's day only (by date label; undated days are treated as today)
- Excludes soups, salads, starters, desserts (`_EXCLUDE` list in `ranking.py`)
- Skips `fodmap=High + fitness=Low` combinations entirely
- Scores: FODMAP (Low=3, Moderate=2, High=1) + Fitness (High=3, Medium=2, Low=1), max 6
- Deduplicates by name, returns highest-scored first

## Key modules

| File | Responsibility |
| --- | --- |
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

#### 1. Unit tests

```bash
python -m pytest tests/ -v
```

All tests must pass. Tests cover: `ranking.py` (date parsing, dish scoring, today detection) and `html/components.py` (date parsing).

#### 2. HTML output check

Generate the site locally (requires `secrets.json` with valid keys) and inspect output:

```bash
python run.py
```

Then verify `results/index.html`:

- Contains `id="cards-grid"` and `id="weekend-msg"`
- Weekend JS block present: `_dow === 0 || _dow === 6`
- Footer contains timestamp
- Each restaurant card has either a "Zobrazit celé menu" or "Menu z minulého dne" button, or a "Menu nedostupné" block

#### 3. Weekend behaviour

Open `results/index.html` in a browser and check the browser console:

- On a weekday: cards grid is visible, weekend message hidden
- On a weekend: cards grid hidden, `🛋️` weekend message visible
- Can be simulated by temporarily patching `new Date().getDay()` in DevTools

#### 4. FTP upload check

If `ftp_host` is set in `secrets.json`, confirm each restaurant file and `index.html` are uploaded — check `processor.py` log output for `"Uploaded to FTP:"` lines.

#### 5. Oracle trigger check

```bash
~/tacek/deploy/trigger_github.sh
```

Must print `HTTP 204`. Anything else means the PAT is expired or has wrong scope (`workflow` required).

#### 6. Cron timing check

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
