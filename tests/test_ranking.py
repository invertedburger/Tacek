from datetime import datetime
import pytest
from tacek.ranking import get_top_dishes, has_today_menu, _parse_date, _is_main_dish, _clean_name


def _today_label():
    now = datetime.now()
    return f"{now.day}.{now.month}.{now.year}"


def _dish(name, fodmap='Low', fitness='High'):
    return {'name': name, 'fodmap_level': fodmap, 'fitness_level': fitness}


def _day(label, dishes):
    return {'day': label, 'dishes': dishes}


# ── _parse_date ───────────────────────────────────────────────

def test_parse_date_full():
    assert _parse_date('Pondělí 31.3.2026') == '2026-03-31'

def test_parse_date_short():
    assert _parse_date('1.4.') == f'{datetime.now().year}-04-01'

def test_parse_date_no_match():
    assert _parse_date('Tuesday') is None

def test_parse_date_invalid_day():
    assert _parse_date('32.13.2026') is None


# ── has_today_menu ────────────────────────────────────────────

def test_has_today_menu_true():
    data = {'days': [_day(_today_label(), [_dish('Svíčková')])]}
    assert has_today_menu(data) is True

def test_has_today_menu_false():
    data = {'days': [_day('1.1.2000', [_dish('Svíčková')])]}
    assert has_today_menu(data) is False

def test_has_today_menu_no_date_label():
    # day with no parseable date is treated as today
    data = {'days': [_day('Dnešní nabídka', [_dish('Svíčková')])]}
    assert has_today_menu(data) is True

def test_has_today_menu_empty():
    assert has_today_menu({'days': []}) is False


# ── get_top_dishes ────────────────────────────────────────────

def test_get_top_dishes_returns_today_only():
    data = {
        'days': [
            _day('1.1.2000', [_dish('Old dish', fodmap='Low', fitness='High')]),
            _day(_today_label(), [_dish('Kuřecí řízek', fodmap='Low', fitness='High')]),
        ]
    }
    result = get_top_dishes(data)
    assert len(result) == 1
    assert result[0]['name'] == 'Kuřecí řízek'

def test_get_top_dishes_returns_empty_when_no_today():
    data = {'days': [_day('1.1.2000', [_dish('Old dish')])]}
    assert get_top_dishes(data) == []

def test_get_top_dishes_excludes_soups():
    data = {
        'days': [_day(_today_label(), [
            _dish('Polévka zeleninová', fodmap='Low', fitness='High'),
            _dish('Kuřecí řízek', fodmap='Low', fitness='High'),
        ])]
    }
    result = get_top_dishes(data)
    names = [d['name'] for d in result]
    assert 'Polévka zeleninová' not in names
    assert 'Kuřecí řízek' in names

def test_get_top_dishes_max_n():
    dishes = [_dish(f'Dish {i}') for i in range(10)]
    data = {'days': [_day(_today_label(), dishes)]}
    assert len(get_top_dishes(data, n=3)) <= 3

def test_get_top_dishes_ranks_low_fodmap_first():
    data = {
        'days': [_day(_today_label(), [
            _dish('Bad dish',  fodmap='High', fitness='Low'),
            _dish('Good dish', fodmap='Low',  fitness='High'),
            _dish('Ok dish',   fodmap='Moderate', fitness='Medium'),
        ])]
    }
    result = get_top_dishes(data)
    assert result[0]['name'] == 'Good dish'

def test_get_top_dishes_skips_high_fodmap_low_fitness():
    data = {
        'days': [_day(_today_label(), [
            _dish('Junk', fodmap='High', fitness='Low'),
        ])]
    }
    assert get_top_dishes(data) == []

def test_has_today_menu_mixed_days():
    """If at least one day matches today, returns True even with stale days."""
    data = {
        'days': [
            _day('1.1.2000', [_dish('Old dish')]),
            _day(_today_label(), [_dish('Today dish')]),
        ]
    }
    assert has_today_menu(data) is True


def test_get_top_dishes_no_duplicate_names():
    data = {
        'days': [_day(_today_label(), [
            _dish('Svíčková'),
            _dish('Svíčková'),
            _dish('Řízek'),
        ])]
    }
    result = get_top_dishes(data)
    names = [d['name'] for d in result]
    assert len(names) == len(set(names))


# ── _is_main_dish ─────────────────────────────────────────────────────────────

def test_is_main_dish_accepts_main_course():
    assert _is_main_dish('Kuřecí řízek') is True

def test_is_main_dish_rejects_soup():
    assert _is_main_dish('Polévka zeleninová') is False

def test_is_main_dish_rejects_salad():
    assert _is_main_dish('Salát Caesar') is False

def test_is_main_dish_rejects_dessert():
    assert _is_main_dish('Dezert čokoládový') is False

def test_is_main_dish_rejects_starter():
    assert _is_main_dish('Předkrm z lososa') is False

def test_is_main_dish_case_insensitive():
    assert _is_main_dish('POLÉVKA') is False

def test_is_main_dish_soup_in_english():
    assert _is_main_dish('Soup of the day') is False


# ── _clean_name ───────────────────────────────────────────────────────────────

def test_clean_name_strips_uppercase_prefix():
    assert _clean_name('HLAVNÍ: Svíčková') == 'Svíčková'

def test_clean_name_strips_diacritics_prefix():
    assert _clean_name('POLÉVKA: Gulášová') == 'Gulášová'

def test_clean_name_leaves_normal_names_unchanged():
    assert _clean_name('Kuřecí řízek') == 'Kuřecí řízek'

def test_clean_name_strips_surrounding_whitespace():
    assert _clean_name('  Svíčková  ') == 'Svíčková'
