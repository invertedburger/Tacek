"""End-to-end smoke test: one full site build with no network and no AI.

This is the manual checklist from CLAUDE.md ("HTML output check") turned into a
test, so a broken page is caught here instead of on the live site the next
morning. It exercises the real processor → ranking → html path; only the
network and the model calls are stubbed.
"""
import json
import os

import pytest

from tacek import processor
from tacek.logger import init_logger, log


WEEKLY_MENU = {
    'days': [
        {'day': 'Pondělí 21.9.2026', 'dishes': [
            {'name': 'Svíčková na smetaně', 'fodmap_level': 'Low', 'fitness_level': 'High',
             'problematic_ingredients': [], 'protein_g': 35, 'carbs_g': 60, 'fat_g': 20,
             'calories_kcal': 560},
            {'name': 'Hovězí vývar', 'fodmap_level': 'Low', 'fitness_level': 'Medium',
             'problematic_ingredients': [], 'protein_g': 8, 'carbs_g': 5, 'fat_g': 3,
             'calories_kcal': 80},
        ]},
        {'day': 'Úterý 22.9.2026', 'dishes': [
            {'name': 'Kuřecí steak', 'fodmap_level': 'Low', 'fitness_level': 'High',
             'problematic_ingredients': [], 'protein_g': 40, 'carbs_g': 30, 'fat_g': 12,
             'calories_kcal': 450},
        ]},
    ]
}


@pytest.fixture
def site(tmp_path, monkeypatch):
    """Build the whole site into tmp_path and return it."""
    monkeypatch.setattr(processor.config, 'RESULTS_DIR', str(tmp_path))
    monkeypatch.setattr(processor.config, 'DOWNLOAD_DIR', str(tmp_path))
    monkeypatch.setattr(processor.config, 'RESTAURANT_DISPLAY_NAMES', {
        'good.example': 'Dobrá restaurace',
        'broken.example': 'Rozbitá restaurace',
    })
    monkeypatch.setattr(processor.config, 'WEBPAGE_PARSERS', {})
    monkeypatch.setattr(processor.config, 'RESTAURANT_NAMES', {})
    monkeypatch.setattr(processor.config, 'RESTAURANT_COORDS_OVERRIDE', {})
    monkeypatch.setattr(processor, 'download_webpage', lambda url: '<html>menu</html>')
    monkeypatch.setattr(processor, 'extract_menu_text', lambda html: 'menu text' * 40)
    monkeypatch.setattr(processor, 'upload', lambda *a, **k: None)
    monkeypatch.setattr(processor, 'geocode', lambda sources: sources)
    # Today is one of the menu's days, so the card is a live one.
    monkeypatch.setattr(processor, 'has_today_menu', lambda d: True)

    def analyze(text, source_name):
        return None if 'broken' in source_name else json.loads(json.dumps(WEEKLY_MENU))

    monkeypatch.setattr(processor, 'analyze_text', analyze)

    init_logger(str(tmp_path))
    log('Starting Tácek menu scraper...')
    sources = processor.process_all_webpages(
        ['https://good.example/menu/', 'https://broken.example/menu/'])
    processor.create_index_html(str(tmp_path), sources)
    from tacek.logger import get_logger
    get_logger().save()
    processor.create_logs_html(str(tmp_path))
    return tmp_path


def _read(site, name):
    return (site / name).read_text(encoding='utf-8')


# ── the files a run must leave behind ─────────────────────────────────────────

def test_build_writes_every_page(site):
    for name in ('index.html', 'profile.html', 'logs.html',
                 'good_example_results.html', 'good_example_data.json'):
        assert (site / name).exists(), f"missing {name}"


def test_failed_restaurant_gets_no_data_file(site):
    assert not (site / 'broken_example_results.html').exists()


# ── index.html: the CLAUDE.md checklist ───────────────────────────────────────

def test_index_has_cards_grid_and_weekend_message(site):
    html = _read(site, 'index.html')
    assert 'id="cards-grid"' in html
    assert 'id="weekend-msg"' in html


def test_index_has_weekend_javascript(site):
    assert '_dow === 0 || _dow === 6' in _read(site, 'index.html')


def test_index_footer_carries_a_timestamp(site):
    import re
    assert re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', _read(site, 'index.html'))


def test_every_card_offers_a_menu_or_says_it_is_unavailable(site):
    html = _read(site, 'index.html')
    assert 'card.view_menu' in html or 'card.stale_menu' in html
    assert 'card.unavailable' in html          # the broken restaurant's card


def test_index_names_both_restaurants(site):
    html = _read(site, 'index.html')
    assert 'Dobrá restaurace' in html
    assert 'Rozbitá restaurace' in html


def test_index_is_balanced_html(site):
    html = _read(site, 'index.html')
    assert html.count('<div') == html.count('</div>')
    assert html.lstrip().startswith('<!DOCTYPE html>')
    assert html.rstrip().endswith('</html>')


# ── the menu page and the log page ────────────────────────────────────────────

def test_menu_page_lists_the_dishes(site):
    html = _read(site, 'good_example_results.html')
    assert 'Svíčková na smetaně' in html
    assert 'Kuřecí steak' in html


def test_menu_page_tags_each_day_with_its_date(site):
    html = _read(site, 'good_example_results.html')
    assert 'data-date="2026-09-21"' in html
    assert 'data-date="2026-09-22"' in html


def test_data_json_survives_the_round_trip(site):
    data = json.loads(_read(site, 'good_example_data.json'))
    assert [d['day'] for d in data['days']] == ['Pondělí 21.9.2026', 'Úterý 22.9.2026']


def test_logs_page_contains_the_run_output(site):
    assert 'Starting Tácek menu scraper' in _read(site, 'logs.html')


def test_logs_page_reports_the_failed_restaurant(site):
    assert 'Rozbitá restaurace' in _read(site, 'logs.html') or \
           'broken.example' in _read(site, 'logs.html')
