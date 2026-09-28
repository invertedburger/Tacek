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


def test_describe_menu_uses_the_given_day_not_the_clock(capsys):
    # This test once passed only because it ran on a day missing from the data.
    data = {'days': [{'day': 'Pátek 25.9.2026', 'dishes': [{'name': 'A'}]}]}
    processor.describe_menu(data, 'Kometa Pub', today='2026-09-21')
    assert 'NOT for today' in capsys.readouterr().out
    processor.describe_menu(data, 'Kometa Pub', today='2026-09-25')
    assert 'has today' in capsys.readouterr().out


# ── 2026-09-25: a card with a menu but no dishes on the main page ─────────────

KOMETA_FRIDAY = {'days': [{'day': 'Pátek 25. 9. 2026', 'dishes': [
    {'name': 'Hrachová kaše s uzeným masem a cibulkou, okurka, pečivo',
     'fodmap_level': 'High', 'fitness_level': 'Low', 'protein_g': 28, 'carbs_g': 70, 'fiber_g': 14},
    {'name': 'Hermelín v bramboráku, nakládaná řepa',
     'fodmap_level': 'High', 'fitness_level': 'Low', 'protein_g': 22, 'carbs_g': 55, 'fiber_g': 5},
    {'name': 'Kuřecí gyros, hranolky, tatarská omáčka',
     'fodmap_level': 'High', 'fitness_level': 'Low', 'protein_g': 32, 'carbs_g': 65, 'fiber_g': 4},
]}]}


def test_all_unsuitable_day_still_lists_its_mains():
    """Kometa Pub cooked three High-FODMAP/Low-fitness mains; the card went blank."""
    by_day = get_top_dishes_by_day(KOMETA_FRIDAY, fallback=True)
    assert len(by_day['2026-09-25']) == 3
    assert all(d['suitable'] is False for d in by_day['2026-09-25'])


def test_fallback_is_opt_in():
    # Recommendations proper (get_top_dishes) must stay strict.
    assert get_top_dishes_by_day(KOMETA_FRIDAY) == {}


def test_fallback_never_mixes_with_real_picks():
    data = {'days': [{'day': 'Pátek 25. 9. 2026', 'dishes': [
        {'name': 'Gyros, hranolky', 'fodmap_level': 'High', 'fitness_level': 'Low'},
        {'name': 'Grilované kuře, rýže', 'fodmap_level': 'Low', 'fitness_level': 'High'},
    ]}]}
    picks = get_top_dishes_by_day(data, fallback=True)['2026-09-25']
    assert [d['name'] for d in picks] == ['Grilované kuře, rýže']
    assert 'suitable' not in picks[0]


def test_fallback_still_skips_soups_and_desserts():
    data = {'days': [{'day': 'Pátek 25. 9. 2026', 'dishes': [
        {'name': 'Gulášová polévka', 'fodmap_level': 'High', 'fitness_level': 'Low'},
        {'name': 'Dukátové buchtičky s krémem', 'fodmap_level': 'High', 'fitness_level': 'Low'},
    ]}]}
    assert get_top_dishes_by_day(data, fallback=True) == {}


def _card(by_day, build_day='2026-09-25'):
    return {'name': 'Kometa Pub', 'url': 'https://www.kometapub.cz/arena',
            'result_file': 'www_kometapub_cz_results.html', 'last_updated': f'{build_day} 11:37',
            'top_dishes': [], 'rec_date': build_day, 'stale_menu': False,
            'top_by_day': by_day, 'menu_dates': sorted(by_day)}


def test_fallback_card_says_nothing_suitable_instead_of_recommending():
    by_day = get_top_dishes_by_day(KOMETA_FRIDAY, fallback=True)
    html = index_page.generate([_card(by_day)], '2026-09-25 11:37', '2026-09-25')
    assert 'Hrachová kaše' in html
    assert 'data-fallback' in html
    # the "nothing suitable" heading is the visible one, "recommended" is hidden
    assert 'data-kind="fallback" data-i18n' in html
    assert 'data-kind="recommend" hidden' in html
    assert '🥇' not in html                       # no medals for unsuitable food
    assert 'opacity-60' in html


def test_normal_card_keeps_the_recommend_heading():
    data = {'days': [{'day': 'Pátek 25. 9. 2026', 'dishes': [
        {'name': 'Grilované kuře, rýže', 'fodmap_level': 'Low', 'fitness_level': 'High'}]}]}
    html = index_page.generate([_card(get_top_dishes_by_day(data, fallback=True))],
                               '2026-09-25 11:37', '2026-09-25')
    assert 'data-kind="recommend" data-i18n' in html
    assert 'data-kind="fallback" hidden' in html
    assert '🥇' in html


def test_client_switches_heading_per_day():
    html = index_page.generate([_card(get_top_dishes_by_day(KOMETA_FRIDAY, fallback=True))],
                               '2026-09-25 11:37', '2026-09-25')
    assert "dated.hasAttribute('data-fallback')" in html
    assert "querySelectorAll('.rec-heading')" in html


# ── 2026-09-25: coloured macros on the card ───────────────────────────────────

def test_card_shows_protein_carbs_and_fiber():
    by_day = get_top_dishes_by_day(KOMETA_FRIDAY, fallback=True)
    html = index_page.generate([_card(by_day)], '2026-09-25 11:37', '2026-09-25')
    assert '28&nbsp;g <span data-i18n="macro.protein">' in html
    assert '70&nbsp;g <span data-i18n="macro.carbs">' in html
    assert '14&nbsp;g <span data-i18n="macro.fiber">' in html


def test_each_macro_has_its_own_colour():
    html = index_page._macros({'protein_g': 30, 'carbs_g': 40, 'fiber_g': 6})
    assert 'bg-sky-500' in html and 'bg-orange-400' in html and 'bg-lime-500' in html


def test_macros_missing_from_older_analyses_are_skipped():
    # Data analysed before fiber_g existed has only protein and carbs.
    html = index_page._macros({'protein_g': 30, 'carbs_g': 40})
    assert 'macro.fiber' not in html
    assert 'macro.protein' in html


def test_no_macros_no_empty_line():
    assert index_page._macros({}) == ''


def test_ranking_carries_macros_through():
    picks = get_top_dishes_by_day({'days': [{'day': 'Pátek 25. 9. 2026', 'dishes': [
        {'name': 'Grilované kuře', 'fodmap_level': 'Low', 'fitness_level': 'High',
         'protein_g': 40, 'carbs_g': 35, 'fiber_g': 5, 'fat_g': 12}]}]})['2026-09-25']
    assert picks[0]['protein_g'] == 40 and picks[0]['carbs_g'] == 35 and picks[0]['fiber_g'] == 5
    assert 'fat_g' not in picks[0]                 # the card shows only what was asked for


def test_non_numeric_macro_is_ignored():
    picks = get_top_dishes_by_day({'days': [{'day': 'Pátek 25. 9. 2026', 'dishes': [
        {'name': 'Grilované kuře', 'fodmap_level': 'Low', 'fitness_level': 'High',
         'protein_g': '?', 'carbs_g': None}]}]})['2026-09-25']
    assert 'protein_g' not in picks[0] and 'carbs_g' not in picks[0]


def test_prompt_asks_for_fiber():
    assert '"fiber_g"' in analyzer.JSON_PROMPT


# ── 2026-09-27: model misread the year, the guard threw the day away ──────────

_CS_DAYS = ('Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle')


def _label(d, year=None):
    return f'{_CS_DAYS[d.weekday()]} {d.day}. {d.month}. {year or d.year}'


def test_misread_year_is_corrected_not_blanked():
    """Eatology's PDF says "Úterý 29. 9. 2026"; the model returned 2025. Blanking
    it made Tuesday undated, and an undated day on a weekly menu only counts
    for the day it was built — so Tuesday's picks would never have shown."""
    from datetime import date, timedelta
    d = date.today() + timedelta(days=2)
    data = {'days': [{'day': _label(d, d.year - 1), 'dishes': [{'name': 'Kuře'}]}]}
    processor.drop_impossible_dates(data, 'Eatology')
    assert data['days'][0]['day'] == _label(d)
    assert _parse_date(data['days'][0]['day']) == d.strftime('%Y-%m-%d')


def test_year_is_not_corrected_when_the_weekday_disagrees():
    from datetime import date, timedelta
    d = date.today() + timedelta(days=2)
    wrong_day = _CS_DAYS[(d.weekday() + 1) % 7]
    data = {'days': [{'day': f'{wrong_day} {d.day}. {d.month}. {d.year - 1}', 'dishes': []}]}
    processor.drop_impossible_dates(data, 'test')
    assert data['days'][0]['day'] == ''


def test_month_misprint_still_blanks():
    # U Tesaře's "22. 6. 2026": no year change brings June near September.
    data = {'days': [{'day': '22. 6. 2026', 'dishes': []}]}
    processor.drop_impossible_dates(data, 'U Tesaře')
    assert data['days'][0]['day'] == ''


def test_year_correction_without_weekday_name():
    from datetime import date, timedelta
    d = date.today() + timedelta(days=1)
    data = {'days': [{'day': f'{d.day}. {d.month}. {d.year - 1}', 'dishes': []}]}
    processor.drop_impossible_dates(data, 'test')
    assert data['days'][0]['day'] == f'{d.day}. {d.month}. {d.year}'


def test_every_day_of_a_weekly_menu_survives_one_misread_year():
    from datetime import date, timedelta
    monday = date.today() - timedelta(days=date.today().weekday()) + timedelta(days=7)
    week = [monday + timedelta(days=i) for i in range(5)]
    data = {'days': [{'day': _label(d, d.year - 1 if i == 1 else None), 'dishes': []}
                     for i, d in enumerate(week)]}
    processor.drop_impossible_dates(data, 'Eatology')
    assert [_parse_date(x['day']) for x in data['days']] == [d.strftime('%Y-%m-%d') for d in week]


# ── Analysis version: a fix has to reach menus that didn't change ─────────────

def test_fresh_analysis_is_stamped_with_the_current_version():
    data = processor.stamp({'days': []})
    assert data['_analysis'] == analyzer.ANALYSIS_VERSION


def _wire(monkeypatch, tmp_path, analyze):
    monkeypatch.setattr(processor.config, 'RESULTS_DIR', str(tmp_path))
    monkeypatch.setattr(processor.config, 'DOWNLOAD_DIR', str(tmp_path))
    monkeypatch.setattr(processor.config, 'RESTAURANT_DISPLAY_NAMES', {'good.example': 'Good'})
    monkeypatch.setattr(processor.config, 'WEBPAGE_PARSERS', {})
    monkeypatch.setattr(processor, 'download_webpage', lambda url: '<html>menu</html>')
    monkeypatch.setattr(processor, 'extract_menu_text', lambda html: 'same menu text')
    monkeypatch.setattr(processor, 'upload', lambda *a, **k: None)
    monkeypatch.setattr(processor, 'has_today_menu', lambda d: True)
    monkeypatch.setattr(processor.menu_page, 'generate', lambda *a, **k: '<html/>')
    monkeypatch.setattr(processor, 'analyze_text', analyze)


def test_unchanged_menu_from_an_older_analysis_is_redone_once(tmp_path, monkeypatch):
    analyze = MagicMock(return_value={'days': [{'day': 'Úterý', 'dishes': []}]})
    _wire(monkeypatch, tmp_path, analyze)
    url = ['https://good.example/menu/']
    processor.process_all_webpages(url)                  # analysed, stamped
    assert analyze.call_count == 1

    # Simulate a cache written before versioning existed.
    path = tmp_path / 'good_example_data.json'
    old = json.loads(path.read_text(encoding='utf-8'))
    old.pop('_analysis')
    path.write_text(json.dumps(old), encoding='utf-8')

    processor.process_all_webpages(url)                  # same text, old version → redo
    assert analyze.call_count == 2
    processor.process_all_webpages(url)                  # now current → cache hit
    assert analyze.call_count == 2


def test_redo_does_not_claim_the_content_is_new(tmp_path, monkeypatch):
    # Re-analysing unchanged text must keep its first-seen date, or an old
    # undated poster would pass for today's.
    analyze = MagicMock(return_value={'days': [{'day': '', 'dishes': []}]})
    _wire(monkeypatch, tmp_path, analyze)
    url = ['https://good.example/menu/']
    processor.process_all_webpages(url)
    log_path = tmp_path / 'processed_webpages.log'
    first = log_path.read_text(encoding='utf-8')
    path = tmp_path / 'good_example_data.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    data.pop('_analysis')
    path.write_text(json.dumps(data), encoding='utf-8')
    processor.process_all_webpages(url)
    assert log_path.read_text(encoding='utf-8') == first


# ── 2026-09-28: Groq's incomplete answers accepted as the week's menu ─────────

PALADAR_TEXT = ('Týdenní menu | 28. 9. - 2.10. 2026 | Pondělí | Státní svátek zavřeno | '
                'Úterý | 150g Španělský ptáček | Středa | Kuřecí steak | Čtvrtek | Drůbeží vývar | '
                'Pátek | Steak z vepřové panenky')


def _dishes(n):
    return [{'name': f'Jídlo {i}'} for i in range(n)]


def test_null_label_junk_day_is_dropped():
    """{"day": null, "dishes": []} parsed as undated → counted as today → the
    broken answer stuck in the cache for the week."""
    menu = analyzer._parse(json.dumps({'days': [
        {'day': None, 'dishes': []},
        {'day': 'Čtvrtek 1.10.2026', 'dishes': _dishes(5)},
    ]}))
    assert [d['day'] for d in menu['days']] == ['Čtvrtek 1.10.2026']


def test_null_label_with_dishes_becomes_undated_not_none():
    menu = analyzer._parse(json.dumps({'days': [{'day': None, 'dishes': _dishes(2)}]}))
    assert menu['days'][0]['day'] == ''


def test_missing_half_the_week_is_weak():
    # The live answer for Il Paladar: Thursday and Friday only.
    broken = {'days': [{'day': 'Čtvrtek 1.10.2026', 'dishes': _dishes(5)},
                       {'day': 'Pátek 2.10.2026', 'dishes': _dishes(5)}]}
    assert analyzer._weakness(broken, PALADAR_TEXT)


def test_closed_holiday_missing_is_not_weak():
    # Monday was a state holiday; Tue-Fri is a complete week.
    ok = {'days': [{'day': f'{d} 2026', 'dishes': _dishes(5)}
                   for d in ('Úterý 29.9.', 'Středa 30.9.', 'Čtvrtek 1.10.', 'Pátek 2.10.')]}
    assert analyzer._weakness(ok, PALADAR_TEXT) is None


def test_no_dishes_at_all_is_weak():
    # The live answer for Kometa: empty Mon/Sat/Sun, Tue-Fri gone.
    broken = {'days': [{'day': 'PONDĚLÍ 28. 9. 2026', 'dishes': []},
                       {'day': 'SOBOTA 3. 10. 2026', 'dishes': []}]}
    assert analyzer._weakness(broken) == 'no dishes'


def test_uppercase_weekdays_count_as_coverage():
    ok = {'days': [{'day': f'{d} 2026', 'dishes': _dishes(3)}
                   for d in ('ÚTERÝ 29. 9.', 'STŘEDA 30. 9.', 'ČTVRTEK 1. 10.', 'PÁTEK 2. 10.')]}
    assert analyzer._weakness(ok, 'PONDĚLÍ ÚTERÝ STŘEDA ČTVRTEK PÁTEK') is None


def test_daily_menu_is_not_judged_by_weekday_coverage():
    # A single-day text naming one weekday can't be "half the week missing".
    one_day = {'days': [{'day': 'Úterý 29.9.2026', 'dishes': _dishes(4)}]}
    assert analyzer._weakness(one_day, 'Úterý 29.9.2026 polední menu') is None


def _groq_returning(payload):
    mock = MagicMock()
    mock.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=json.dumps(payload)))]
    return mock


def _gemini_returning(payload):
    mock = MagicMock()
    mock.models.generate_content.return_value.text = json.dumps(payload)
    return mock


def test_weak_groq_answer_is_replaced_by_a_fuller_gemini_one():
    broken = {'days': [{'day': 'Čtvrtek 1.10.2026', 'dishes': _dishes(5)},
                       {'day': 'Pátek 2.10.2026', 'dishes': _dishes(5)}]}
    full = {'days': [{'day': f'{d} 2026', 'dishes': _dishes(6)}
                     for d in ('Úterý 29.9.', 'Středa 30.9.', 'Čtvrtek 1.10.', 'Pátek 2.10.')]}
    with patch.object(analyzer, '_groq', _groq_returning(broken)), \
         patch.object(analyzer, '_gemini', _gemini_returning(full)):
        assert analyzer.analyze_text(PALADAR_TEXT, 'Il Paladar') == full


def test_weak_groq_answer_kept_when_gemini_is_worse():
    broken = {'days': [{'day': 'Čtvrtek 1.10.2026', 'dishes': _dishes(5)}]}
    with patch.object(analyzer, '_groq', _groq_returning(broken)), \
         patch.object(analyzer, '_gemini', _gemini_returning({'days': []})):
        assert analyzer.analyze_text(PALADAR_TEXT, 'Il Paladar') == broken


def test_weak_groq_answer_kept_when_gemini_is_down():
    broken = {'days': [{'day': 'Čtvrtek 1.10.2026', 'dishes': _dishes(5)}]}
    down = MagicMock()
    down.models.generate_content.side_effect = Exception('403 PERMISSION_DENIED')
    with patch.object(analyzer, '_groq', _groq_returning(broken)), \
         patch.object(analyzer, '_gemini', down):
        assert analyzer.analyze_text(PALADAR_TEXT, 'Il Paladar') == broken


def test_complete_groq_answer_skips_gemini():
    full = {'days': [{'day': f'{d} 2026', 'dishes': _dishes(6)}
                     for d in ('Úterý 29.9.', 'Středa 30.9.', 'Čtvrtek 1.10.', 'Pátek 2.10.')]}
    gemini = _gemini_returning({'days': []})
    with patch.object(analyzer, '_groq', _groq_returning(full)), \
         patch.object(analyzer, '_gemini', gemini):
        assert analyzer.analyze_text(PALADAR_TEXT, 'Il Paladar') == full
    gemini.models.generate_content.assert_not_called()


def test_version_was_bumped_for_the_gate():
    # The broken Paladar answer is cached; only a new version re-analyses it.
    assert analyzer.ANALYSIS_VERSION >= 3
