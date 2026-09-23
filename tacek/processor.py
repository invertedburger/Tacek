import os
import json
from urllib.parse import urlparse
from datetime import datetime, timedelta

from tacek import config
from tacek.downloader import (
    download_file, download_webpage, download_image, resolve_pdf_link,
    extract_menu_text, find_menu_images, file_hash, text_hash, image_content_hash,
)
from tacek.analyzer import analyze_pdf, analyze_text, analyze_image
from tacek.ftp import upload
from tacek.ranking import (
    get_top_dishes, get_top_dishes_by_day, has_today_menu, menu_dates, recommend_date,
    _parse_date,
)
from tacek.geocoder import geocode
from tacek.html import menu_page, index_page, profile_page, logs_page
from tacek.logger import log


# A menu may legitimately run two weeks ahead; anything further is a misprint.
_MAX_DATE_DRIFT_DAYS = 14


def drop_impossible_dates(data, source_name):
    """Blank a day label dated nowhere near today, so a typo can't hide a menu.

    Restaurants do misprint their posters — U Tesaře published the 22. 9. menu
    headed "22. 6. 2026" — and a date months out would mark a perfectly current
    menu as not-for-today. Undated hands freshness back to the content hash,
    which is exactly how undated posters are already handled.
    """
    today = datetime.now().date()
    for day in data.get('days', []):
        label = day.get('day', '')
        parsed = _parse_date(label)
        if not parsed:
            continue
        drift = abs((datetime.strptime(parsed, '%Y-%m-%d').date() - today).days)
        if drift > _MAX_DATE_DRIFT_DAYS:
            log(f"WARNING: {source_name} menu dated '{label}' is {drift} days from today "
                f"— looks like a misprint, treating it as undated.")
            day['day'] = ''
    return data


def split_links(pdf_links, webpage_links):
    # pdf_links are explicitly declared PDF sources — even if the entry points at
    # a page that the PDF link is resolved from (see resolve_pdf_link), not a
    # direct .pdf. webpage_links are still routed by their .pdf suffix.
    pdfs = [url for url in pdf_links if url.strip()]
    webpages = []
    for url in webpage_links:
        if urlparse(url).path.lower().endswith('.pdf'):
            pdfs.append(url)
        elif url.strip():
            webpages.append(url)
    return pdfs, webpages


def process_all_pdfs(pdf_links):
    log_path = os.path.join(config.RESULTS_DIR, 'processed_files.log')
    processed = _load_log(log_path)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    today = datetime.now().strftime('%Y-%m-%d')
    sources = []

    for url in pdf_links:
        # Identity (data files, display name) is keyed on the *config* URL's domain,
        # so it stays stable even when the resolved PDF lives on dynamic storage.
        domain = urlparse(url).netloc
        source_name = domain.replace('.', '_')
        restaurant_name = config.RESTAURANT_DISPLAY_NAMES.get(domain, domain)

        pdf_url = resolve_pdf_link(url)
        pdf_path = download_file(pdf_url, config.DOWNLOAD_DIR) if pdf_url else None
        if pdf_path is None:
            log(f"Skipping {restaurant_name} — download failed.")
            sources.append({'name': restaurant_name, 'url': url, 'result_file': None, 'last_updated': timestamp, 'no_menu': True})
            continue
        fhash = file_hash(pdf_path)
        result_name = f"{source_name}_results.html"
        data_name   = f"{source_name}_data.json"
        result_path = os.path.join(config.RESULTS_DIR, result_name)
        data_path   = os.path.join(config.RESULTS_DIR, data_name)

        # Log value is "hash|first_seen_date"; legacy entries are bare "hash".
        prev_hash, _, prev_date = str(processed.get(source_name, '')).partition('|')

        data = None
        # Cache key is the stable source_name (not the filename, which can change
        # weekly on dynamic PDF URLs); freshness is decided by the content hash.
        if source_name in processed and prev_hash == fhash and os.path.exists(data_path):
            cached = _load_json(data_path)
            if has_today_menu(cached):
                log(f"No change in {source_name}, regenerating HTML from cache.")
                data = cached
            else:
                log(f"Cache for {source_name} is stale, re-analyzing...")

        content_changed = prev_hash != fhash
        kept_last_good = False
        if data is None:
            log(f"Analyzing {pdf_path} with Gemini...")
            data = analyze_pdf(pdf_path)
            if data is None:
                # Same reasoning as the webpage path: keep the last good menu
                # over a blank card when the analysis itself fell over.
                previous = _load_json(data_path) if os.path.exists(data_path) else None
                if not previous:
                    log(f"No menu data for {source_name}, marking as unavailable.")
                    sources.append({'name': restaurant_name, 'url': url, 'result_file': None, 'last_updated': timestamp, 'no_menu': True})
                    continue
                log(f"Analysis failed for {source_name}, keeping the last known menu.")
                data = previous
                kept_last_good = True
            else:
                _save_json(drop_impossible_dates(data, source_name), data_path)

        # Same first-seen anchoring as the webpage path, so an undated PDF menu
        # can't keep masquerading as "today" (see ranking.recommend_date).
        seen_date = today if (content_changed and not kept_last_good) else (prev_date or 'unknown')
        if not kept_last_good:
            processed[source_name] = f"{fhash}|{seen_date}"
            _save_log(processed, log_path)

        _write_and_upload(menu_page.generate(data, restaurant_name, url, timestamp), result_path, result_name)
        upload(data_path, data_name)
        sources.append({'name': restaurant_name, 'url': url, 'result_file': result_name,
                        'last_updated': timestamp, 'content_seen_date': seen_date})

    return sources


def process_all_webpages(webpage_links):
    log_path = os.path.join(config.RESULTS_DIR, 'processed_webpages.log')
    processed = _load_log(log_path)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    today = datetime.now().strftime('%Y-%m-%d')
    sources = []

    for url in webpage_links:
        domain       = urlparse(url).netloc
        source_name  = domain.replace('.', '_')
        result_name  = f"{source_name}_results.html"
        data_name    = f"{source_name}_data.json"
        result_path  = os.path.join(config.RESULTS_DIR, result_name)
        data_path    = os.path.join(config.RESULTS_DIR, data_name)
        restaurant_name = config.RESTAURANT_DISPLAY_NAMES.get(domain, domain)
        parser = config.WEBPAGE_PARSERS.get(domain, 'auto')

        html_content = download_webpage(url)
        if html_content is None:
            log(f"Skipping {restaurant_name} — download failed.")
            sources.append({'name': restaurant_name, 'url': url, 'result_file': None, 'last_updated': timestamp, 'no_menu': True})
            continue
        menu_text = extract_menu_text(html_content)

        if parser == 'image':
            image_urls = find_menu_images(html_content, url)
            cache_key  = image_content_hash(image_urls)
        else:
            cache_key  = text_hash(menu_text)
            image_urls = []

        # Log value is "hash|first_seen_date"; legacy entries are bare "hash".
        prev_hash, _, prev_date = str(processed.get(url, '')).partition('|')

        data = None
        if url in processed and cache_key is not None and prev_hash == cache_key and os.path.exists(data_path):
            cached = _load_json(data_path)
            if has_today_menu(cached):
                log(f"No change in {url}, regenerating HTML from cache.")
                data = cached
            else:
                log(f"Cache for {url} is stale, re-analyzing...")

        # A None cache_key means an image fetch failed — freshness is unknown,
        # so it must not count as changed content or clobber the last good hash.
        content_changed = cache_key is not None and prev_hash != cache_key
        kept_last_good = False
        if data is None:
            log(f"Analyzing {url} with Gemini...")
            data = _fetch_and_analyze(parser, html_content, url, menu_text, image_urls, source_name)
            if data is None:
                # A failed analysis is usually a provider outage, not a closed
                # restaurant. The last good menu, flagged as old, beats a blank
                # card — and the hash stays put so the next run tries again.
                previous = _load_json(data_path) if os.path.exists(data_path) else None
                if not previous:
                    log(f"No menu data for {url}, marking as unavailable.")
                    sources.append({'name': restaurant_name, 'url': url, 'result_file': None, 'last_updated': timestamp, 'no_menu': True})
                    continue
                log(f"Analysis failed for {url}, keeping the last known menu.")
                data = previous
                kept_last_good = True
            else:
                _save_json(drop_impossible_dates(data, source_name), data_path)

        # Anchor undated menus to the date their content was first seen, so a
        # stale/unchanged image can't keep masquerading as "today" (see
        # ranking.recommend_date). Changed content == today; an unchanged legacy
        # entry with no recorded date is "unknown" → treated as not-today.
        seen_date = today if (content_changed and not kept_last_good) else (prev_date or 'unknown')
        if cache_key is not None and not kept_last_good:
            processed[url] = f"{cache_key}|{seen_date}"
            _save_log(processed, log_path)

        _write_and_upload(menu_page.generate(data, restaurant_name, url, timestamp), result_path, result_name)
        upload(data_path, data_name)
        sources.append({'name': restaurant_name, 'url': url, 'result_file': result_name,
                        'last_updated': timestamp, 'content_seen_date': seen_date})

    return sources


def create_logs_html(results_dir):
    log_path = os.path.join(results_dir, 'run_log.json')
    if os.path.exists(log_path):
        log_data = _load_json(log_path)
    else:
        log_data = None

    logs_html = logs_page.generate(log_data)
    logs_path = os.path.join(results_dir, 'logs.html')
    with open(logs_path, 'w', encoding='utf-8') as f:
        f.write(logs_html)
    log(f"Logs page written to {logs_path}")
    upload(logs_path, 'logs.html')


def create_index_html(results_dir, sources):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    today = datetime.now().strftime('%Y-%m-%d')
    sources = geocode(sources)

    for src in sources:
        if src.get('no_menu') or not src.get('result_file'):
            src['top_dishes'] = []
            src['top_by_day'] = {}
            src['menu_dates'] = []
            src['rec_date'] = None
            continue
        data_path = os.path.join(results_dir, src['result_file'].replace('_results.html', '_data.json'))
        try:
            data = _load_json(data_path)
            src['top_dishes'] = get_top_dishes(data)
            src['stale_menu'] = not has_today_menu(data)
            src['rec_date'] = recommend_date(data)
            # Carry every day from today on, so a weekly menu can serve the right
            # day's picks on later mornings before that day's build has fired.
            # Days already past can never match a future viewing date, so they're
            # dropped to keep index.html small.
            src['top_by_day'] = {k: v for k, v in get_top_dishes_by_day(data).items()
                                 if k == '' or k >= today}
            src['menu_dates'] = sorted(d for d in menu_dates(data) if d == '' or d >= today)
            # Freshness guard: an undated menu (recommend_date == '') is only
            # really "today" if its content was first seen today. Otherwise a
            # stale, unchanged image would keep showing as the current day.
            # Dated days gate themselves against the viewer's clock; the undated
            # bucket has no date to check, so it is what gets dropped here.
            seen = src.get('content_seen_date')
            if seen is not None and seen != today and src['rec_date'] == '':
                src['stale_menu'] = True
                src['top_dishes'] = []
                src['rec_date'] = None
                src['top_by_day'].pop('', None)
                src['menu_dates'] = [d for d in src['menu_dates'] if d != '']
        except Exception:
            # Unreadable data → don't advertise it as today's menu.
            src['top_dishes'] = []
            src['top_by_day'] = {}
            src['menu_dates'] = []
            src['stale_menu'] = True
            src['rec_date'] = None

    index_path = os.path.join(results_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_page.generate(sources, timestamp, today))
    log(f"Index page written to {index_path}")
    upload(index_path, 'index.html')

    profile_path = os.path.join(results_dir, 'profile.html')
    with open(profile_path, 'w', encoding='utf-8') as f:
        f.write(profile_page.generate())
    log(f"Profile page written to {profile_path}")
    upload(profile_path, 'profile.html')


# ── helpers ──────────────────────────────────────────────────

def _fetch_and_analyze(parser, html_content, url, menu_text, image_urls, source_name):
    if parser == 'image' or (parser == 'auto' and len(menu_text.strip()) < config.MIN_MENU_TEXT_LENGTH):
        if not image_urls:
            image_urls = find_menu_images(html_content, url)
        if image_urls:
            log(f"Found {len(image_urls)} menu image(s), analyzing...")
            merged = {'days': []}
            for img_url in image_urls:
                try:
                    img_path = download_image(img_url, config.DOWNLOAD_DIR)
                    if img_path is None:
                        continue
                    img_data = analyze_image(img_path)
                    if img_data:
                        merged['days'].extend(img_data.get('days', []))
                except Exception as e:
                    log(f"WARNING: Failed to process image {img_url}: {e}")
            return merged if merged['days'] else None
        log("No menu images found, falling back to text analysis.")
    return analyze_text(menu_text, source_name)


def _load_log(path):
    result = {}
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    result[parts[0]] = parts[1]
    return result


def _save_log(data, path):
    with open(path, 'w') as f:
        for k, v in data.items():
            f.write(f"{k},{v}\n")


def _load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_and_upload(html, local_path, remote_name):
    with open(local_path, 'w', encoding='utf-8') as f:
        f.write(html)
    log(f"Saved {local_path}")
    upload(local_path, remote_name)
