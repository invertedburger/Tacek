import pytest
from tacek.html.components import parse_date
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
