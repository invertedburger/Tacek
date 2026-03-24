import os
import json
import time
import requests
from urllib.parse import urlparse
from tacek.config import RESTAURANT_NAMES, RESTAURANT_COORDS_OVERRIDE, RESULTS_DIR


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
        print(f"Geocoding: {query}...")
        try:
            r = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': query, 'format': 'json', 'limit': 1},
                headers={'User-Agent': 'Tácek/1.0'},
                timeout=10
            )
            data = r.json()
            if data:
                coords = [float(data[0]['lat']), float(data[0]['lon'])]
                cache[domain] = coords
                src['coords'] = coords
                changed = True
                print(f"  -> {coords}")
            else:
                print(f"  -> not found")
        except Exception as e:
            print(f"  -> error: {e}")
        time.sleep(1)

    if changed:
        with open(coords_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2)

    return sources
