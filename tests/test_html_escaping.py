"""Scraped/AI-derived strings (dish names, day labels, ingredients) must be
HTML-escaped when interpolated into the generated pages."""
from tacek.html import menu_page, index_page


def _menu_data(name='Svíčková na smetaně', day='Pondělí 6.7.2026', ingredients=None):
    return {'days': [{'day': day, 'dishes': [{
        'name': name,
        'fodmap_level': 'Low',
        'fitness_level': 'High',
        'problematic_ingredients': ingredients or [],
        'protein_g': 30, 'carbs_g': 40, 'fat_g': 15, 'calories_kcal': 415,
    }]}]}


def test_menu_page_escapes_dish_name():
    data = _menu_data(name='<script>alert(1)</script>')
    out = menu_page.generate(data, 'Test', 'https://example.com', '2026-07-11 10:00')
    assert '<script>alert(1)</script>' not in out
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in out


def test_menu_page_escapes_day_label_and_ingredients():
    data = _menu_data(day='Pondělí <b>6.7.2026</b>', ingredients=['<img src=x onerror=alert(1)>'])
    out = menu_page.generate(data, 'Test', 'https://example.com', '2026-07-11 10:00')
    assert '<b>6.7.2026</b>' not in out
    assert '<img src=x onerror=alert(1)>' not in out
    assert '&lt;b&gt;6.7.2026&lt;/b&gt;' in out


def test_menu_page_keeps_czech_names_intact():
    out = menu_page.generate(_menu_data(), 'Test', 'https://example.com', '2026-07-11 10:00')
    assert 'Svíčková na smetaně' in out
    assert 'Pondělí 6.7.2026' in out


def test_index_page_escapes_dish_name():
    sources = [{
        'name': 'Test', 'url': 'https://example.com', 'result_file': 'test_results.html',
        'last_updated': '2026-07-11 10:00', 'rec_date': '',
        'top_dishes': [{'name': '<script>x</script>', 'fodmap': 'Low', 'fitness': 'High',
                        'score': 6, 'today': True}],
    }]
    out = index_page.generate(sources, '2026-07-11 10:00')
    assert '<script>x</script>' not in out
    assert '&lt;script&gt;x&lt;/script&gt;' in out


def test_index_page_card_carries_rec_date():
    sources = [{
        'name': 'Test', 'url': 'https://example.com', 'result_file': 'test_results.html',
        'last_updated': '2026-07-11 10:00', 'rec_date': '',
        'top_dishes': [],
    }]
    out = index_page.generate(sources, '2026-07-11 10:00')
    # Attribute lives on the card even when there is no recommend-section.
    assert 'data-rec-date=""' in out
    assert "#cards-grid [data-rec-date]" in out
