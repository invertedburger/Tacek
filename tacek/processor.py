import os
import json
from urllib.parse import urlparse
from datetime import datetime

from tacek import config
from tacek.downloader import (
    download_file, download_webpage, download_image,
    extract_menu_text, find_menu_images, file_hash, text_hash, image_content_hash,
)
from tacek.analyzer import analyze_pdf, analyze_text, analyze_image
from tacek.ftp import upload
from tacek.ranking import get_top_dishes
from tacek.geocoder import geocode
from tacek.html import menu_page, index_page, profile_page


def split_links(pdf_links, webpage_links):
    pdfs, webpages = [], []
    for url in pdf_links + webpage_links:
        if url.lower().endswith('.pdf'):
            pdfs.append(url)
        elif url.strip():
            webpages.append(url)
    return pdfs, webpages


def process_all_pdfs(pdf_links):
    log_path = os.path.join(config.RESULTS_DIR, 'processed_files.log')
    processed = _load_log(log_path)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    sources = []

    for url in pdf_links:
        pdf_path = download_file(url, config.DOWNLOAD_DIR)
        fhash = file_hash(pdf_path)
        fname = os.path.basename(pdf_path)
        domain = urlparse(url).netloc
        source_name = domain.replace('.', '_')
        result_name = f"{source_name}_results.html"
        data_name   = f"{source_name}_data.json"
        result_path = os.path.join(config.RESULTS_DIR, result_name)
        data_path   = os.path.join(config.RESULTS_DIR, data_name)
        restaurant_name = config.RESTAURANT_DISPLAY_NAMES.get(domain, domain)

        if fname in processed and processed[fname] == fhash and os.path.exists(data_path):
            print(f"No change in {fname}, regenerating HTML from cache.")
            data = _load_json(data_path)
        else:
            print(f"Analyzing {pdf_path} with Gemini...")
            data = analyze_pdf(pdf_path)
            if data is None:
                print(f"No menu data for {fname}, marking as unavailable.")
                sources.append({'name': restaurant_name, 'url': url, 'result_file': None, 'last_updated': timestamp, 'no_menu': True})
                continue
            _save_json(data, data_path)
            processed[fname] = fhash
            _save_log(processed, log_path)

        _write_and_upload(menu_page.generate(data, restaurant_name, url, timestamp), result_path, result_name)
        upload(data_path, data_name)
        sources.append({'name': restaurant_name, 'url': url, 'result_file': result_name, 'last_updated': timestamp})

    return sources


def process_all_webpages(webpage_links):
    log_path = os.path.join(config.RESULTS_DIR, 'processed_webpages.log')
    processed = _load_log(log_path)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    sources = []

    for url in webpage_links:
        html_content = download_webpage(url)
        menu_text    = extract_menu_text(html_content)
        domain       = urlparse(url).netloc
        source_name  = domain.replace('.', '_')
        result_name  = f"{source_name}_results.html"
        data_name    = f"{source_name}_data.json"
        result_path  = os.path.join(config.RESULTS_DIR, result_name)
        data_path    = os.path.join(config.RESULTS_DIR, data_name)
        restaurant_name = config.RESTAURANT_DISPLAY_NAMES.get(domain, domain)
        parser = config.WEBPAGE_PARSERS.get(domain, 'auto')

        if parser == 'image':
            image_urls = find_menu_images(html_content, url)
            cache_key  = image_content_hash(image_urls)
        else:
            cache_key  = text_hash(menu_text)
            image_urls = []

        if url in processed and processed[url] == cache_key and os.path.exists(data_path):
            print(f"No change in {url}, regenerating HTML from cache.")
            data = _load_json(data_path)
        else:
            print(f"Analyzing {url} with Gemini...")
            data = _fetch_and_analyze(parser, html_content, url, menu_text, image_urls, source_name)
            if data is None:
                print(f"No menu data for {url}, marking as unavailable.")
                sources.append({'name': restaurant_name, 'url': url, 'result_file': None, 'last_updated': timestamp, 'no_menu': True})
                continue
            _save_json(data, data_path)
            processed[url] = cache_key
            _save_log(processed, log_path)

        _write_and_upload(menu_page.generate(data, restaurant_name, url, timestamp), result_path, result_name)
        upload(data_path, data_name)
        sources.append({'name': restaurant_name, 'url': url, 'result_file': result_name, 'last_updated': timestamp})

    return sources


def create_index_html(results_dir, sources):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    sources = geocode(sources)

    for src in sources:
        if src.get('no_menu') or not src.get('result_file'):
            src['top_dishes'] = []
            continue
        data_path = os.path.join(results_dir, src['result_file'].replace('_results.html', '_data.json'))
        try:
            src['top_dishes'] = get_top_dishes(_load_json(data_path))
        except Exception:
            src['top_dishes'] = []

    index_path = os.path.join(results_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_page.generate(sources, timestamp))
    print(f"Index page written to {index_path}")
    upload(index_path, 'index.html')

    profile_path = os.path.join(results_dir, 'profile.html')
    with open(profile_path, 'w', encoding='utf-8') as f:
        f.write(profile_page.generate())
    print(f"Profile page written to {profile_path}")
    upload(profile_path, 'profile.html')


# ── helpers ──────────────────────────────────────────────────

def _fetch_and_analyze(parser, html_content, url, menu_text, image_urls, source_name):
    if parser == 'image' or (parser == 'auto' and len(menu_text.strip()) < config.MIN_MENU_TEXT_LENGTH):
        if not image_urls:
            image_urls = find_menu_images(html_content, url)
        if image_urls:
            print(f"Found {len(image_urls)} menu image(s), analyzing...")
            merged = {'days': []}
            for img_url in image_urls:
                try:
                    img_path = download_image(img_url, config.DOWNLOAD_DIR)
                    img_data = analyze_image(img_path)
                    if img_data:
                        merged['days'].extend(img_data.get('days', []))
                except Exception as e:
                    print(f"WARNING: Failed to process image {img_url}: {e}")
            return merged if merged['days'] else None
        print("No menu images found, falling back to text analysis.")
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
    print(f"Saved {local_path}")
    upload(local_path, remote_name)
