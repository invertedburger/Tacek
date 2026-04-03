import os
import hashlib
import requests
from urllib.parse import urlparse, urljoin
from datetime import datetime
from bs4 import BeautifulSoup
from tacek.logger import log

try:
    import cloudscraper
    _scraper = cloudscraper.create_scraper()
    log("cloudscraper available — using anti-bot bypass")
except ImportError:
    _scraper = None

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}


def _get(url, **kwargs):
    """Use cloudscraper if available, else requests."""
    if _scraper:
        return _scraper.get(url, **kwargs)
    return requests.get(url, headers=_HEADERS, **kwargs)


def download_file(url, dest_folder):
    filename = os.path.basename(urlparse(url).path) or f"menu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    dest_path = os.path.join(dest_folder, filename)
    log(f"Downloading {url}...")
    r = _get(url, timeout=30)
    log(f"Downloaded {len(r.content)} bytes, status {r.status_code}")
    if r.status_code != 200:
        log(f"WARNING: Download failed with status {r.status_code}")
        return None
    with open(dest_path, 'wb') as f:
        f.write(r.content)
    return dest_path


def download_webpage(url):
    log(f"Downloading web page: {url}...")
    r = _get(url, timeout=30)
    r.encoding = r.apparent_encoding
    log(f"Downloaded {len(r.text)} chars from {url}")
    return r.text


def download_image(url, dest_folder):
    filename = os.path.basename(urlparse(url).path)
    if not filename or '.' not in filename:
        filename = f"menu_img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    dest_path = os.path.join(dest_folder, filename)
    log(f"Downloading menu image: {url}...")
    r = _get(url, timeout=30)
    log(f"Downloaded image: {len(r.content)} bytes, {r.status_code}, saved as {filename}")
    with open(dest_path, 'wb') as f:
        f.write(r.content)
    return dest_path


def extract_menu_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    main = soup.find('main') or soup.body or soup
    return main.get_text(separator='\n', strip=True)


def find_menu_images(html, page_url):
    soup = BeautifulSoup(html, 'html.parser')
    keywords = ['menu', 'jidel', 'nabidka', 'denni', 'tydenni', 'lunch', 'poledni']
    images = _collect_images(soup, page_url, keywords)
    if images:
        return images
    # Fallback: find recent WordPress upload images (not logos/headers)
    return _find_wp_content_images(soup, page_url)


def _collect_images(soup, page_url, keywords):
    import re as _re
    best = {}

    def _add(src, width=0):
        src = src.strip()
        if not src or not any(kw in src.lower() for kw in keywords):
            return
        url = urljoin(page_url, src)
        base = _re.sub(r'-\d+x\d+(\.[^.]+)$', r'\1', os.path.basename(url))
        if base not in best or width > best[base][1]:
            best[base] = (url, width)

    for img in soup.find_all('img'):
        for attr in ('src', 'data-src', 'data-lazy-src', 'data-orig-file'):
            val = img.get(attr, '')
            if val:
                _add(val)
        for attr in ('srcset', 'data-srcset'):
            srcset = img.get(attr, '')
            if srcset:
                for part in srcset.split(','):
                    parts = part.strip().split()
                    if not parts:
                        continue
                    url_part = parts[0]
                    w = int(parts[1].rstrip('w')) if len(parts) > 1 and parts[1].endswith('w') else 0
                    _add(url_part, w)

    return [url for url, _ in best.values()]


def _find_wp_content_images(soup, page_url):
    """Fallback: find WordPress upload images that are not logos or header banners."""
    now = datetime.now()
    results = []
    skip_classes = {'custom-logo', 'wp-post-image'}
    for img in soup.find_all('img'):
        classes = set(img.get('class', []))
        if classes & skip_classes:
            continue
        src = img.get('src') or img.get('data-src') or ''
        if not src:
            continue
        url = urljoin(page_url, src)
        # Only WordPress uploads from recent months
        if 'wp-content/uploads/' not in url:
            continue
        # Check the upload path contains current or recent year/month
        for delta in range(3):
            m = now.month - delta
            y = now.year
            if m < 1:
                m += 12
                y -= 1
            if f'/{y}/{m:02d}/' in url:
                log(f"Fallback image found: {url}")
                results.append(url)
                break
    return results


def file_hash(path):
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def text_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def image_content_hash(urls):
    sha = hashlib.sha256()
    for url in sorted(urls):
        try:
            r = _get(url, timeout=15)
            sha.update(r.content)
        except Exception:
            sha.update(url.encode('utf-8'))
    return sha.hexdigest()
