import os
import hashlib
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

from tacek.downloader import (
    file_hash, text_hash, image_content_hash,
    extract_menu_text, find_menu_images,
    download_file, download_webpage, download_image,
)


# ── helpers ──────────────────────────────────────────────────────────────────

class _Resp:
    def __init__(self, content=b'', text='', status_code=200, encoding='utf-8'):
        self.content = content
        self.text = text
        self.status_code = status_code
        self.encoding = encoding
        self.apparent_encoding = encoding


# ── hashing ──────────────────────────────────────────────────────────────────

def test_file_hash_matches_sha256(tmp_path):
    f = tmp_path / 'data.bin'
    f.write_bytes(b'hello world')
    assert file_hash(str(f)) == hashlib.sha256(b'hello world').hexdigest()


def test_file_hash_is_consistent(tmp_path):
    f = tmp_path / 'data.bin'
    f.write_bytes(b'abc')
    assert file_hash(str(f)) == file_hash(str(f))


def test_file_hash_differs_on_different_content(tmp_path):
    a = tmp_path / 'a.bin'
    b = tmp_path / 'b.bin'
    a.write_bytes(b'aaa')
    b.write_bytes(b'bbb')
    assert file_hash(str(a)) != file_hash(str(b))


def test_text_hash_matches_sha256():
    assert text_hash('hello') == hashlib.sha256(b'hello').hexdigest()


def test_text_hash_differs_on_different_strings():
    assert text_hash('aaa') != text_hash('bbb')


def test_image_content_hash_uses_content():
    with patch('tacek.downloader._get', return_value=_Resp(content=b'img1')):
        h1 = image_content_hash(['https://example.com/a.jpg'])
    with patch('tacek.downloader._get', return_value=_Resp(content=b'img2')):
        h2 = image_content_hash(['https://example.com/a.jpg'])
    assert h1 != h2


def test_image_content_hash_falls_back_on_network_error():
    with patch('tacek.downloader._get', side_effect=Exception('timeout')):
        result = image_content_hash(['https://example.com/a.jpg'])
    assert len(result) == 64  # still returns a sha256 hex


def test_image_content_hash_is_order_independent():
    def _get_by_url(url, **kw):
        return _Resp(content=url.encode())

    with patch('tacek.downloader._get', side_effect=_get_by_url):
        h1 = image_content_hash(['https://example.com/a.jpg', 'https://example.com/b.jpg'])
    with patch('tacek.downloader._get', side_effect=_get_by_url):
        h2 = image_content_hash(['https://example.com/b.jpg', 'https://example.com/a.jpg'])
    assert h1 == h2  # sorted internally


# ── text extraction ───────────────────────────────────────────────────────────

def test_extract_menu_text_uses_main_tag():
    html = '<html><body><main>Main content</main><footer>Footer</footer></body></html>'
    result = extract_menu_text(html)
    assert 'Main content' in result
    assert 'Footer' not in result


def test_extract_menu_text_falls_back_to_body():
    html = '<html><body><p>Body only</p></body></html>'
    assert 'Body only' in extract_menu_text(html)


def test_extract_menu_text_non_empty():
    html = '<html><body><main>  spaced  text  </main></body></html>'
    result = extract_menu_text(html)
    assert result.strip() != ''
    assert 'spaced' in result
    assert 'text' in result


# ── image discovery ───────────────────────────────────────────────────────────

def test_find_menu_images_src_with_menu_keyword():
    html = '<html><body><img src="/wp-content/uploads/menu-2026.jpg"/></body></html>'
    result = find_menu_images(html, 'https://example.com')
    assert any('menu' in u for u in result)


def test_find_menu_images_excludes_non_menu_images():
    html = '<html><body><img src="/images/logo.jpg"/></body></html>'
    result = find_menu_images(html, 'https://example.com')
    assert result == []


def test_find_menu_images_from_srcset_picks_largest():
    # Deduplication uses the WxH pattern (e.g. -400x300); width-only descriptors
    # like -400w are treated as distinct filenames, so both URLs are returned.
    # Use an NxN-suffixed pair to exercise the deduplication path.
    html = '''<html><body>
      <img srcset="/menu-400x300.jpg 400w, /menu-800x600.jpg 800w"/>
    </body></html>'''
    result = find_menu_images(html, 'https://example.com')
    assert len(result) == 1  # deduplicated to the larger one


def test_find_menu_images_data_src_lazy():
    html = '<html><body><img data-src="/wp-content/uploads/poledni-menu.jpg"/></body></html>'
    result = find_menu_images(html, 'https://example.com')
    assert len(result) > 0


def test_find_menu_images_wp_content_fallback():
    now = datetime.now()
    y, m = now.year, f'{now.month:02d}'
    html = f'<html><body><img src="/wp-content/uploads/{y}/{m}/image.jpg"/></body></html>'
    result = find_menu_images(html, 'https://example.com')
    assert len(result) > 0


def test_find_menu_images_wp_content_fallback_skips_logos():
    now = datetime.now()
    y, m = now.year, f'{now.month:02d}'
    html = f'''<html><body>
      <img class="custom-logo" src="/wp-content/uploads/{y}/{m}/logo.jpg"/>
    </body></html>'''
    result = find_menu_images(html, 'https://example.com')
    assert result == []


# ── HTTP helpers ─────────────────────────────────────────────────────────────

def test_download_file_success(tmp_path):
    with patch('tacek.downloader._get', return_value=_Resp(content=b'%PDF', status_code=200)):
        path = download_file('https://example.com/menu.pdf', str(tmp_path))
    assert path is not None
    assert os.path.exists(path)
    assert open(path, 'rb').read() == b'%PDF'


def test_download_file_returns_none_on_http_error(tmp_path):
    with patch('tacek.downloader._get', return_value=_Resp(content=b'', status_code=404)):
        result = download_file('https://example.com/menu.pdf', str(tmp_path))
    assert result is None


def test_download_file_uses_url_basename(tmp_path):
    with patch('tacek.downloader._get', return_value=_Resp(content=b'data', status_code=200)):
        path = download_file('https://example.com/menu.pdf', str(tmp_path))
    assert os.path.basename(path) == 'menu.pdf'


def test_download_webpage_returns_text():
    with patch('tacek.downloader._get', return_value=_Resp(text='<html>Hello</html>')):
        result = download_webpage('https://example.com/lunch/')
    assert 'Hello' in result


def test_download_image_saves_file(tmp_path):
    with patch('tacek.downloader._get', return_value=_Resp(content=b'\xff\xd8\xff' + b'x' * 10)):
        path = download_image('https://example.com/menu.jpg', str(tmp_path))
    assert os.path.exists(path)
    assert os.path.basename(path) == 'menu.jpg'


def test_download_image_generates_name_for_no_extension(tmp_path):
    with patch('tacek.downloader._get', return_value=_Resp(content=b'data')):
        path = download_image('https://example.com/image', str(tmp_path))
    assert os.path.exists(path)
