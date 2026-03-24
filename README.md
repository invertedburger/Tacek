# Tácek

Automated lunch menu analyzer for restaurants near Holandská, Brno. Fetches menus daily (PDFs, web pages, or images), analyzes them with Google Gemini, and publishes a static HTML site with FODMAP and fitness ratings.

## Features

- Scrapes menus from PDFs, web pages, and image-based menus
- AI analysis via Google Gemini — FODMAP level, fitness rating, macros
- Hash-based caching — only re-analyzes when content changes
- Per-restaurant parser configuration (`text`, `image`, or `auto`)
- Publishes results to FTP as a static site
- Interactive filters (FODMAP / Fitness), dark mode, Leaflet map

## Project Structure

```
Tacek/
├── run.py                  # Entry point
├── config.json             # Restaurant list and settings
├── secrets.json            # API keys and FTP credentials (not committed)
├── requirements.txt
├── menus/                  # Downloaded PDFs and images (not committed)
├── results/                # Generated HTML and JSON (not committed)
└── tacek/
    ├── config.py           # Loads config.json + secrets.json
    ├── downloader.py       # HTTP fetching, HTML/image extraction, hashing
    ├── analyzer.py         # Gemini API calls (PDF / text / image)
    ├── ranking.py          # Top dish scoring (FODMAP + fitness)
    ├── geocoder.py         # Nominatim geocoding with cache
    ├── ftp.py              # FTP upload
    ├── processor.py        # Orchestration and cache logic
    └── html/
        ├── assets.py       # Shared CSS and JS strings
        ├── components.py   # head(), header(), badge helpers
        ├── menu_page.py    # Per-restaurant menu page generator
        ├── index_page.py   # Main index page generator
        └── profile_page.py # Diet preferences page generator
```

## Setup

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Create `secrets.json`**

```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY",
  "ftp_host": "your.ftp.host",
  "ftp_user": "username",
  "ftp_pass": "password",
  "ftp_dir": "/public_html"
}
```

Get a Gemini API key at [aistudio.google.com](https://aistudio.google.com).

**3. Run**

```bash
python run.py
```

Results are written to `results/` and uploaded to FTP.

## Configuration

All restaurant settings live in `config.json`:

```json
{
  "pdf_links": ["https://example.com/menu.pdf"],
  "webpage_links": ["https://example.com/menu/"],
  "restaurant_display_names": {
    "www.example.com": "My Restaurant"
  },
  "webpage_parsers": {
    "www.example.com": "image"
  }
}
```

### Parser types

| Value | Behavior |
|-------|----------|
| `"auto"` | Uses text if long enough, falls back to image detection (default) |
| `"text"` | Always scrapes page text |
| `"image"` | Always looks for menu images; cache key is based on image URLs |

Use `"image"` for restaurants that post their menu as a photo (e.g. a scanned weekly menu). This fixes stale caches when images change but the surrounding page text does not.

### Adding a restaurant

1. Add the URL to `pdf_links` or `webpage_links` in `config.json`
2. Add a display name to `restaurant_display_names`
3. Add a geocoding query to `restaurant_names` (used for the map)
4. If the menu is image-based, add `"www.domain.com": "image"` to `webpage_parsers`

No code changes needed.

## Caching

The script avoids unnecessary Gemini API calls:

- **PDFs** — cached by file hash
- **Text pages** — cached by hash of extracted page text
- **Image pages** — cached by hash of sorted image URLs on the page

To force a re-analysis, delete the relevant line from `results/processed_webpages.log` or `results/processed_files.log`.

## Output

Each run produces:

| File | Description |
|------|-------------|
| `results/index.html` | Main page listing all restaurants |
| `results/profile.html` | Diet preference settings |
| `results/<domain>_results.html` | Per-restaurant menu page |
| `results/<domain>_data.json` | Raw Gemini output (used for caching) |
| `results/coords.json` | Geocoding cache |

All files are uploaded to FTP after generation.
