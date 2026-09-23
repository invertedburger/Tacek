"""One test per failure that actually reached production.

Every case here broke the live site at least once, so each test names the day
it broke and what the symptom was. Add to this file whenever a run goes wrong:
a bug that got out once is the one most likely to come back.
"""
import json
import os
from unittest.mock import MagicMock, patch

import pytest

import tacek.analyzer as analyzer
from tacek import processor
from tacek.html import index_page
from tacek.ranking import _parse_date, get_top_dishes_by_day, has_today_menu


# ── 2026-09-21: whole run aborted, site stuck on the previous build ───────────

def test_model_returning_a_bare_list_does_not_crash():
    """Groq answered with the day list itself; .get('days') raised AttributeError
    and took down every restaurant, not just this one."""
    days = [{'day': 'Pondělí 21.9.2026', 'dishes': [{'name': 'Svíčková'}]}]
    assert analyzer._parse(json.dumps(days)) == {'days': days}


def test_model_returning_a_single_day_object_is_wrapped():
    day = {'day': 'Pondělí 21.9.2026', 'dishes': [{'name': 'Svíčková'}]}
    assert analyzer._parse(json.dumps(day)) == {'days': [day]}


def test_model_returning_days_under_another_key_is_recovered():
    payload = {'menu': [{'day': 'Úterý', 'dishes': []}]}
    assert analyzer._parse(json.dumps(payload)) == {'days': payload['menu']}


def test_analyze_text_survives_a_list_answer():
    days = [{'day': 'Pondělí', 'dishes': [{'name': 'Guláš'}]}]
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=json.dumps(days)))]
    with patch.object(analyzer, '_groq', mock_groq):
        assert analyzer.analyze_text('menu', 'test') == {'days': days}


def test_parse_rejects_a_scalar_answer():
    with pytest.raises(Exception):
        analyzer._parse('"just a string"')


def test_one_restaurant_crashing_leaves_the_others_alone(tmp_path, monkeypatch):
    """The guard that stops a single bad answer from costing everyone their menu."""
    monkeypatch.setattr(processor.config, 'RESULTS_DIR', str(tmp_path))
    monkeypatch.setattr(processor.config, 'DOWNLOAD_DIR', str(tmp_path))
    monkeypatch.setattr(processor.config, 'RESTAURANT_DISPLAY_NAMES',
                        {'good.example': 'Good', 'bad.example': 'Bad'})
    monkeypatch.setattr(processor.config, 'WEBPAGE_PARSERS', {})
    monkeypatch.setattr(processor, 'download_webpage', lambda url: '<html>menu</html>')
    monkeypatch.setattr(processor, 'extract_menu_text', lambda html: 'menu text')
    monkeypatch.setattr(processor, 'upload', lambda *a, **k: None)
    monkeypatch.setattr(processor, 'has_today_menu', lambda d: True)
    monkeypatch.setattr(processor.menu_page, 'generate', lambda *a, **k: '<html/>')

    def analyze(text, source_name):
        if 'bad' in source_name:
            raise AttributeError("'list' object has no attribute 'get'")
        return {'days': [{'day': 'Pondělí', 'dishes': [{'name': 'Svíčková'}]}]}

    monkeypatch.setattr(processor, 'analyze_text', analyze)
    sources = processor.process_all_webpages(
        ['https://bad.example/menu/', 'https://good.example/menu/'])

    by_name = {s['name']: s for s in sources}
    assert by_name['Bad']['no_menu'] is True
    assert by_name['Good']['result_file'] == 'good_example_results.html'


# ── 2026-09-22: two cards blanked by one-off provider failures ────────────────

def test_transient_provider_error_is_retried():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise Exception('503 UNAVAILABLE. This model is currently experiencing high demand')
        return 'menu'

    with patch.object(analyzer.time, 'sleep', lambda s: None):
        assert analyzer._with_retry(flaky, 'Gemini') == 'menu'
    assert len(calls) == 2


def test_groq_rejecting_its_own_output_is_salvaged():
    """gpt-oss appended stray closers; Groq 400'd but returned the text."""
    menu = {'days': [{'day': 'Středa 23.9.2026', 'dishes': [{'name': 'Kuře'}]}]}
    err = Exception('400 json_validate_failed')
    err.body = {'error': {'failed_generation': json.dumps(menu) + ']}]}'}}
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.side_effect = err
    with patch.object(analyzer, '_groq', mock_groq):
        assert analyzer._groq_text('menu', 'Buddha 2') == menu


# ── 2026-09-18: weekly labels collapsed onto one date ─────────────────────────

def test_week_range_labels_stay_five_distinct_days():
    """Il Paladar dated every day "14. 9. - 18. 9. 2026", so Mon-Thu showed
    "no menu today" and Friday pooled the whole week."""
    data = {'days': [{'day': f'{d} 14. 9. - 18. 9. 2026',
                      'dishes': [{'name': f'Jídlo {d}', 'fodmap_level': 'Low',
                                  'fitness_level': 'High'}]}
                     for d in ('Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek')]}
    assert len(get_top_dishes_by_day(data)) == 5
    assert sorted(get_top_dishes_by_day(data)) == ['2026-09-14', '2026-09-15',
                                                   '2026-09-16', '2026-09-17', '2026-09-18']


# ── 2026-09-22: poster misprinted its own date ────────────────────────────────

def test_misprinted_poster_date_does_not_hide_the_menu():
    """U Tesaře headed the 22. 9. poster "22. 6. 2026"."""
    data = {'days': [{'day': '22. 6. 2026', 'dishes': [{'name': 'Svíčková'}]}]}
    assert has_today_menu(data) is False
    processor.drop_impossible_dates(data, 'U Tesaře')
    assert has_today_menu(data) is True


# ── Monday morning: Friday's picks shown as "recommended today" ───────────────

def _undated_card(build_day):
    picks = [{'name': 'Svíčková', 'fodmap': 'Low', 'fitness': 'High'}]
    return {
        'name': 'U Tesaře',
        'url': 'https://www.utesare.cz/poledni-nabidka/',
        'result_file': 'www_utesare_cz_results.html',
        'last_updated': f'{build_day} 11:37',
        'top_dishes': picks,
        'rec_date': '',
        'content_seen_date': build_day,
        'stale_menu': False,
        'top_by_day': {'': picks},
        'menu_dates': [''],
    }


def test_undated_picks_are_dated_with_the_build_day():
    build_day = '2026-09-18'
    html = index_page.generate([_undated_card(build_day)], f'{build_day} 11:37', build_day)
    assert f'data-rec-date="{build_day}"' in html
    # An empty date would match every later day in the client and keep showing.
    assert 'data-rec-date=""' not in html


def test_client_only_reveals_the_block_matching_the_viewers_day():
    html = index_page.generate([_undated_card('2026-09-18')], '2026-09-18 11:37', '2026-09-18')
    assert "d.getAttribute('data-rec-date') === _today" in html
    assert 'sec.hidden = !dated;' in html


def test_menu_dates_do_not_claim_a_later_day():
    build_day = '2026-09-18'
    html = index_page.generate([_undated_card(build_day)], f'{build_day} 11:37', build_day)
    assert f'data-menu-dates="{build_day}"' in html


# ── Coverage logging: the line that makes the next bug visible ────────────────

def test_describe_menu_reports_span_and_today(capsys):
    data = {'days': [{'day': 'Pondělí 21.9.2026', 'dishes': [{'name': 'A'}]},
                     {'day': 'Pátek 25.9.2026', 'dishes': [{'name': 'B'}, {'name': 'C'}]}]}
    processor.describe_menu(data, 'Eatology', today='2026-09-23')
    out = capsys.readouterr().out
    assert '2 day(s) 2026-09-21…2026-09-25' in out
    assert '3 dishes' in out
    assert 'NOT for today' in out


def test_describe_menu_flags_todays_menu(capsys):
    data = {'days': [{'day': '', 'dishes': [{'name': 'A'}]}]}
    processor.describe_menu(data, 'U Tesaře', today='2026-09-23')
    assert 'has today' in capsys.readouterr().out
