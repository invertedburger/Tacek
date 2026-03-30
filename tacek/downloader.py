import os
import hashlib
import requests
from urllib.parse import urlparse, urljoin
from datetime import datetime
from bs4 import BeautifulSoup


def download_file(url, dest_folder):
    filename = os.path.basename(urlparse(url).path) or f"menu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    dest_path = os.path.join(dest_folder, filename)
    print(f"Downloading {url}...")
    r = requests.get(url, timeout=30)
    with open(dest_path, 'wb') as f:
        f.write(r.content)
    return dest_path


def download_webpage(url):
    print(f"Downloading web page: {url}...")
    r = requests.get(url, timeout=30)
    r.encoding = r.apparent_encoding
    return r.text


def download_image(url, dest_folder):
    filename = os.path.basename(urlparse(url).path)
    if not filename or '.' not in filename:
        filename = f"menu_img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    dest_path = os.path.join(dest_folder, filename)
    print(f"Downloading menu image: {url}...")
    r = requests.get(url, timeout=30)
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
    images = []
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
        if src and any(kw in src.lower() for kw in keywords):
            images.append(urljoin(page_url, src))
    return images


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
            r = requests.get(url, timeout=15)
            sha.update(r.content)
        except Exception:
            sha.update(url.encode('utf-8'))
    return sha.hexdigest()
