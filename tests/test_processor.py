import os
import json
import pytest
from unittest.mock import MagicMock, patch

from tacek import processor, config
from tacek.processor import split_links, _load_json, _save_json, _write_and_upload


# ── split_links ───────────────────────────────────────────────────────────────

def test_split_links_separates_pdf_and_webpage():
    pdfs, pages = split_links(
        ['https://example.com/menu.pdf'],
        ['https://example.com/lunch/'],
    )
    assert pdfs == ['https://example.com/menu.pdf']
    assert pages == ['https://example.com/lunch/']


def test_split_links_detects_pdf_in_webpage_list():
    pdfs, pages = split_links([], ['https://example.com/menu.PDF', 'https://example.com/lunch/'])
    assert 'https://example.com/menu.PDF' in pdfs
    assert 'https://example.com/lunch/' in pages


def test_split_links_skips_empty_strings():
    pdfs, pages = split_links([], ['', '  ', 'https://example.com/lunch/'])
    assert '' not in pages
    assert '  ' not in pages
    assert 'https://example.com/lunch/' in pages


def test_split_links_empty_inputs():
    pdfs, pages = split_links([], [])
    assert pdfs == []
    assert pages == []


def test_split_links_all_pdfs():
    pdfs, pages = split_links(
        ['https://a.com/a.pdf', 'https://b.com/b.pdf'],
        [],
    )
    assert len(pdfs) == 2
    assert pages == []


def test_split_links_pdf_link_page_url_stays_pdf():
    # A pdf_links entry pointing at a PAGE (PDF resolved later) is still a PDF
    # source, even though its path does not end in .pdf.
    pdfs, pages = split_links(['https://www.iqrestaurant.cz/cs/pobocky/brno'], [])
    assert pdfs == ['https://www.iqrestaurant.cz/cs/pobocky/brno']
    assert pages == []


def test_split_links_skips_empty_pdf_entries():
    pdfs, pages = split_links(['', '   ', 'https://a.com/a.pdf'], [])
    assert pdfs == ['https://a.com/a.pdf']


# ── process_all_pdfs: dynamic PDF resolution + stable caching ──────────────────

def _wire_pdf_processor(monkeypatch, tmp_path, resolve, download_content=b'%PDF-1',
                        filename_seq=None):
    """Patch process_all_pdfs' collaborators to run without network/AI/FTP."""
    monkeypatch.setattr(config, 'RESULTS_DIR', str(tmp_path))
    monkeypatch.setattr(config, 'DOWNLOAD_DIR', str(tmp_path))
    monkeypatch.setattr(config, 'RESTAURANT_DISPLAY_NAMES', {'www.iqrestaurant.cz': 'Eatology'})
    monkeypatch.setattr(processor, 'resolve_pdf_link', resolve)

    names = iter(filename_seq) if filename_seq else None

    def fake_download(url, folder):
        fname = next(names) if names else os.path.basename(url)
        path = os.path.join(folder, fname)
        with open(path, 'wb') as f:
            f.write(download_content)
        return path

    monkeypatch.setattr(processor, 'download_file', fake_download)
    monkeypatch.setattr(processor, 'has_today_menu', lambda d: True)
    monkeypatch.setattr(processor, 'upload', lambda *a, **k: None)
    monkeypatch.setattr(processor.menu_page, 'generate', lambda *a, **k: '<html/>')
    analyze = MagicMock(return_value={'days': [{'day': 'Pondělí', 'dishes': []}]})
    monkeypatch.setattr(processor, 'analyze_pdf', analyze)
    return analyze


def test_process_all_pdfs_resolves_page_to_pdf_and_keeps_identity(tmp_path, monkeypatch):
    analyze = _wire_pdf_processor(
        monkeypatch, tmp_path,
        resolve=lambda u: 'https://blob.example/menus/cs/monday-111-abc.pdf',
    )
    sources = processor.process_all_pdfs(['https://www.iqrestaurant.cz/cs/pobocky/brno'])

    assert sources[0]['name'] == 'Eatology'
    assert sources[0]['result_file'] == 'www_iqrestaurant_cz_results.html'
    assert os.path.exists(tmp_path / 'www_iqrestaurant_cz_data.json')
    # Cache key is the stable source_name, not the weekly-changing filename.
    log = (tmp_path / 'processed_files.log').read_text()
    assert 'www_iqrestaurant_cz,' in log
    assert 'monday-111' not in log
    assert analyze.call_count == 1


def test_process_all_pdfs_cache_survives_weekly_filename_change(tmp_path, monkeypatch):
    # Same PDF content served under a new hashed filename each run must NOT force
    # re-analysis — otherwise every run burns an AI call (and could miss/empty out
    # the menu if the AI hiccups).
    analyze = _wire_pdf_processor(
        monkeypatch, tmp_path,
        resolve=lambda u: 'https://blob.example/x.pdf',
        download_content=b'%PDF-IDENTICAL',
        filename_seq=['monday-week1.pdf', 'monday-week2.pdf'],
    )
    page = ['https://www.iqrestaurant.cz/cs/pobocky/brno']
    processor.process_all_pdfs(page)   # first run: analyze
    processor.process_all_pdfs(page)   # second run: new filename, same bytes → cache hit
    assert analyze.call_count == 1


def test_process_all_pdfs_marks_unavailable_when_resolution_fails(tmp_path, monkeypatch):
    # Restaurant changed their page and the PDF link can't be found → the card is
    # marked no_menu rather than crashing the whole run.
    analyze = _wire_pdf_processor(monkeypatch, tmp_path, resolve=lambda u: None)
    sources = processor.process_all_pdfs(['https://www.iqrestaurant.cz/cs/pobocky/brno'])
    assert sources[0]['no_menu'] is True
    assert sources[0]['result_file'] is None
    analyze.assert_not_called()


# ── JSON helpers ──────────────────────────────────────────────────────────────

def test_load_json_reads_data(tmp_path):
    data = {'days': [{'day': 'Monday', 'dishes': []}]}
    f = tmp_path / 'data.json'
    f.write_text(json.dumps(data), encoding='utf-8')
    assert _load_json(str(f)) == data


def test_load_json_preserves_unicode(tmp_path):
    data = {'name': 'Svíčková'}
    f = tmp_path / 'data.json'
    f.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    assert _load_json(str(f))['name'] == 'Svíčková'


def test_save_json_writes_readable_file(tmp_path):
    data = {'days': []}
    f = tmp_path / 'out.json'
    _save_json(data, str(f))
    assert f.exists()
    assert json.loads(f.read_text()) == data


def test_save_json_round_trips(tmp_path):
    original = {'days': [{'day': 'Pondělí', 'dishes': [{'name': 'Řízek', 'fodmap_level': 'Low'}]}]}
    f = tmp_path / 'rt.json'
    _save_json(original, str(f))
    assert _load_json(str(f)) == original


# ── _write_and_upload ─────────────────────────────────────────────────────────

def test_write_and_upload_writes_file(tmp_path):
    out = tmp_path / 'page.html'
    with patch('tacek.processor.upload') as mock_upload:
        _write_and_upload('<html/>', str(out), 'page.html')
    assert out.read_text(encoding='utf-8') == '<html/>'


def test_write_and_upload_calls_upload(tmp_path):
    out = tmp_path / 'page.html'
    with patch('tacek.processor.upload') as mock_upload:
        _write_and_upload('<html/>', str(out), 'page.html')
    mock_upload.assert_called_once_with(str(out), 'page.html')


def test_write_and_upload_overwrites_existing(tmp_path):
    out = tmp_path / 'page.html'
    out.write_text('old content', encoding='utf-8')
    with patch('tacek.processor.upload'):
        _write_and_upload('new content', str(out), 'page.html')
    assert out.read_text(encoding='utf-8') == 'new content'
