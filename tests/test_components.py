import pytest
from tacek.html.components import (
    parse_date, fodmap_badge, fitness_badge, stars_to_level, head, header,
)
from datetime import datetime


def test_parse_date_dd_mm_yyyy():
    assert parse_date('Středa 1.4.2026') == '2026-04-01'

def test_parse_date_with_spaces():
    assert parse_date('1 4 2026') == '2026-04-01'

def test_parse_date_short_no_year():
    result = parse_date('1.4.')
    assert result == f'{datetime.now().year}-04-01'

def test_parse_date_no_date():
    assert parse_date('Žádné datum') is None

def test_parse_date_invalid():
    assert parse_date('99.99.2026') is None

def test_parse_date_tuesday_label():
    assert parse_date('Tuesday 31.3.2026') == '2026-03-31'


# ── fodmap_badge ──────────────────────────────────────────────────────────────

def test_fodmap_badge_low_is_green():
    assert 'green' in fodmap_badge('Low')

def test_fodmap_badge_moderate_is_amber():
    assert 'amber' in fodmap_badge('Moderate')

def test_fodmap_badge_high_is_red():
    assert 'red' in fodmap_badge('High')

def test_fodmap_badge_unknown_is_gray():
    assert 'gray' in fodmap_badge('Unknown')


# ── fitness_badge ─────────────────────────────────────────────────────────────

def test_fitness_badge_high_is_green():
    assert 'green' in fitness_badge('High')

def test_fitness_badge_medium_is_amber():
    assert 'amber' in fitness_badge('Medium')

def test_fitness_badge_low_is_red():
    assert 'red' in fitness_badge('Low')

def test_fitness_badge_unknown_is_gray():
    assert 'gray' in fitness_badge('Unknown')


# ── stars_to_level ────────────────────────────────────────────────────────────

def test_stars_to_level_4_is_high():
    assert stars_to_level(4) == 'High'

def test_stars_to_level_5_is_high():
    assert stars_to_level(5) == 'High'

def test_stars_to_level_3_is_medium():
    assert stars_to_level(3) == 'Medium'

def test_stars_to_level_2_is_low():
    assert stars_to_level(2) == 'Low'

def test_stars_to_level_0_is_low():
    assert stars_to_level(0) == 'Low'

def test_stars_to_level_none_is_low():
    assert stars_to_level(None) == 'Low'


# ── head ──────────────────────────────────────────────────────────────────────

def test_head_contains_title():
    assert 'My Page' in head('My Page')

def test_head_has_charset():
    assert 'UTF-8' in head('x')

def test_head_has_viewport():
    assert 'viewport' in head('x')

def test_head_includes_extra_css():
    assert '.chip{}' in head('x', extra_css='.chip{}')

def test_head_has_cache_control():
    assert 'no-cache' in head('x')


# ── header ────────────────────────────────────────────────────────────────────

def test_header_contains_back_label():
    assert 'Zpět' in header('index.html', 'Zpět', 'Title')

def test_header_contains_title():
    assert 'My Restaurant' in header('index.html', 'Back', 'My Restaurant')

def test_header_back_link_href():
    assert 'index.html' in header('index.html', 'Back', 'Title')

def test_header_right_link_present():
    html = header('index.html', 'Back', 'Title',
                  right_link_href='https://example.com', right_link_text='Originál')
    assert 'Originál' in html
    assert 'https://example.com' in html

def test_header_no_right_link_when_omitted():
    html = header('index.html', 'Back', 'Title')
    assert 'Originál' not in html
