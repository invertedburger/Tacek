import os
import json
import pytest
from unittest.mock import MagicMock, patch

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
