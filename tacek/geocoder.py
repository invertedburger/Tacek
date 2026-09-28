import os
import json
import time
import tempfile
import requests
from urllib.parse import urlparse
from tacek.config import RESTAURANT_NAMES, RESTAURANT_COORDS_OVERRIDE, RESULTS_DIR
from tacek.logger import log


def geocode(sources):
    coords_file = os.path.join(RESULTS_DIR, 'coords.json')
    cache = {}
    if os.path.exists(coords_file):
        with open(coords_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)

    changed = False
    for src in sources:
        domain = urlparse(src['url']).netloc

        if domain in RESTAURANT_COORDS_OVERRIDE:
            src['coords'] = RESTAURANT_COORDS_OVERRIDE[domain]
            cache[domain] = src['coords']
            changed = True
            continue

        if domain in cache:
            src['coords'] = cache[domain]
            continue

        query = RESTAURANT_NAMES.get(domain, f'{domain} Brno Czech Republic')
        log(f"Geocoding: {query}...")
        try:
            r = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': query, 'format': 'json', 'limit': 1},
                headers={'User-Agent': 'Tácek/1.0'},
                timeout=10
            )
            # Handle rate limiting (429 Too Many Requests)
            if r.status_code == 429:
                log(f"  -> rate limited by Nominatim, skipping")
                time.sleep(2)  # Back off longer on rate limit
                continue
            r.raise_for_status()
            data = r.json()
            if data:
                coords = [float(data[0]['lat']), float(data[0]['lon'])]
                cache[domain] = coords
                src['coords'] = coords
                changed = True
                log(f"  -> {coords}")
            else:
                # Fallback: log but continue without coords (don't add 'coords' key)
                log(f"  -> not found (no geocoding)")
        except requests.RequestException as e:
            # Specific handling for request errors (don't add 'coords' key)
            log(f"  -> request error: {e}")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Errors parsing response (don't add 'coords' key)
            log(f"  -> parse error: {e}")
        except Exception as e:
            # Catch-all for unexpected errors (don't add 'coords' key)
            log(f"  -> unexpected error: {type(e).__name__}: {e}")
        time.sleep(1)

    if changed:
        # Atomic write: write to temp file first, then rename
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=RESULTS_DIR,
                delete=False,
                suffix='.json'
            ) as tmp_f:
                tmp_path = tmp_f.name        # before the dump, so a failed dump is cleaned up
                json.dump(cache, tmp_f, indent=2, ensure_ascii=False)
            # Rename is atomic on most systems
            os.replace(tmp_path, coords_file)
            log(f"Updated coords cache: {coords_file}")
        except Exception as e:
            log(f"Error writing coords cache: {e}")
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    return sources
