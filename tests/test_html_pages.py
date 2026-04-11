"""Tests for all four HTML page generators."""
import pytest
from datetime import datetime


# ── helpers ───────────────────────────────────────────────────────────────────

def _src(no_menu=False, stale=False, coords=None):
    base = {
        'name': 'Test Restaurant',
        'url': 'https://example.com/menu/',
        'coords': coords,
    }
    if no_menu:
        return {**base, 'result_file': None, 'no_menu': True, 'top_dishes': []}
    return {
        **base,
        'result_file': 'test_results.html',
        'no_menu': False,
        'stale_menu': stale,
        'last_updated': '2026-04-11 14:00',
        'top_dishes': [{'name': 'Svíčková', 'fodmap': 'High', 'fitness': 'Medium'}],
    }


def _menu_data(dish_name='Svíčková na smetaně', fodmap='High', fitness='Medium'):
    return {
        'days': [{
            'day': 'Pondělí 14.4.2026',
            'dishes': [{
                'name': dish_name,
                'fodmap_level': fodmap,
                'fitness_level': fitness,
                'problematic_ingredients': ['gluten', 'onion'],
                'protein_g': 35,
                'carbs_g': 60,
                'fat_g': 20,
                'calories_kcal': 560,
            }],
        }],
    }


def _log_data(messages=('Starting scraper',)):
    return {
        'start_time': '2026-04-11T10:37:00+02:00',
        'end_time':   '2026-04-11T10:39:00+02:00',
        'logs': [{'time': '2026-04-11T10:38:00+02:00', 'message': m} for m in messages],
    }


# ── index_page ────────────────────────────────────────────────────────────────

class TestIndexPage:
    def _gen(self, sources=None, ts='2026-04-11 14:00'):
        from tacek.html.index_page import generate
        return generate(sources or [_src()], ts)

    def test_valid_html(self):
        html = self._gen()
        assert html.startswith('<!DOCTYPE html>')
        assert '</html>' in html

    def test_cards_grid_element_present(self):
        assert 'id="cards-grid"' in self._gen()

    def test_weekend_msg_element_present(self):
        assert 'id="weekend-msg"' in self._gen()

    def test_weekend_js_dow_check(self):
        assert '_dow === 0 || _dow === 6' in self._gen()

    def test_stale_menu_button(self):
        assert 'Menu z minulého dne' in self._gen([_src(stale=True)])

    def test_fresh_menu_button(self):
        assert 'Zobrazit celé menu' in self._gen([_src(stale=False)])

    def test_no_menu_card(self):
        html = self._gen([_src(no_menu=True)])
        assert 'Menu nedostupné' in html

    def test_restaurant_name_in_output(self):
        assert 'Test Restaurant' in self._gen()

    def test_timestamp_in_footer(self):
        assert '2026-04-11 14:00' in self._gen()

    def test_no_map_when_no_coords(self):
        assert 'id="map"' not in self._gen([_src(coords=None)])

    def test_map_present_when_coords_given(self):
        assert 'id="map"' in self._gen([_src(coords=[49.19, 16.60])])

    def test_top_dish_shown(self):
        assert 'Svíčková' in self._gen()

    def test_multiple_restaurants(self):
        sources = [_src(), _src(no_menu=True)]
        sources[1]['name'] = 'Second Place'
        html = self._gen(sources)
        assert 'Test Restaurant' in html
        assert 'Second Place' in html

    def test_gen_date_in_script(self):
        html = self._gen()
        today = datetime.now().strftime('%Y-%m-%d')
        assert f'"{today}"' in html


# ── menu_page ────────────────────────────────────────────────────────────────

class TestMenuPage:
    def _gen(self, data=None):
        from tacek.html.menu_page import generate
        return generate(data or _menu_data(), 'Test Restaurant', 'https://example.com', '2026-04-11 14:00')

    def test_valid_html(self):
        html = self._gen()
        assert html.startswith('<!DOCTYPE html>')
        assert '</html>' in html

    def test_restaurant_name_in_output(self):
        assert 'Test Restaurant' in self._gen()

    def test_dish_name_in_output(self):
        assert 'Svíčková na smetaně' in self._gen()

    def test_calories_in_output(self):
        assert '560' in self._gen()

    def test_protein_in_output(self):
        assert '35' in self._gen()

    def test_fodmap_badge_high(self):
        assert 'Vysoký FODMAP' in self._gen(_menu_data(fodmap='High'))

    def test_fodmap_badge_low(self):
        assert 'Nízký FODMAP' in self._gen(_menu_data(fodmap='Low'))

    def test_fitness_badge_medium(self):
        assert 'Dobré fitness' in self._gen(_menu_data(fitness='Medium'))

    def test_fitness_badge_high(self):
        assert 'Výborné fitness' in self._gen(_menu_data(fitness='High'))

    def test_problematic_ingredients_shown(self):
        html = self._gen()
        assert 'gluten' in html
        assert 'onion' in html

    def test_day_label_in_output(self):
        assert 'Pondělí' in self._gen()

    def test_empty_days_renders_without_crash(self):
        html = self._gen({'days': []})
        assert 'Test Restaurant' in html

    def test_back_link_to_index(self):
        assert 'index.html' in self._gen()

    def test_dish_links_to_google_images(self):
        html = self._gen()
        assert 'google.com/search' in html

    def test_multiple_dishes(self):
        data = {
            'days': [{
                'day': 'Pondělí',
                'dishes': [
                    {**_menu_data()['days'][0]['dishes'][0], 'name': 'Svíčková'},
                    {**_menu_data()['days'][0]['dishes'][0], 'name': 'Řízek vídeňský'},
                ],
            }],
        }
        html = self._gen(data)
        assert 'Svíčková' in html
        assert 'Řízek vídeňský' in html


# ── logs_page ────────────────────────────────────────────────────────────────

class TestLogsPage:
    def _gen(self, data):
        from tacek.html.logs_page import generate
        return generate(data)

    def test_no_data_shows_empty_message(self):
        assert 'Žádné logy' in self._gen(None)

    def test_no_data_valid_html(self):
        html = self._gen(None)
        assert html.startswith('<!DOCTYPE html>')

    def test_with_data_shows_messages(self):
        html = self._gen(_log_data(['Starting scraper', 'Done']))
        assert 'Starting scraper' in html
        assert 'Done' in html

    def test_error_message_gets_red_color(self):
        html = self._gen(_log_data(['ERROR: something broke']))
        assert 'text-red-600' in html

    def test_warning_message_gets_red_color(self):
        html = self._gen(_log_data(['WARNING: slow response']))
        assert 'text-red-600' in html

    def test_analyzing_message_gets_blue_color(self):
        html = self._gen(_log_data(['Analyzing IQ Restaurant with Gemini...']))
        assert 'text-blue-600' in html

    def test_saved_message_gets_green_color(self):
        html = self._gen(_log_data(['Index page written to results/index.html']))
        assert 'text-green-600' in html

    def test_no_change_message_gets_gray_color(self):
        html = self._gen(_log_data(['No change in menu.pdf, regenerating HTML from cache.']))
        assert 'text-gray-600' in html

    def test_log_count_shown(self):
        html = self._gen(_log_data(['a', 'b', 'c']))
        assert '3' in html

    def test_timestamps_formatted(self):
        html = self._gen(_log_data(['msg']))
        assert '10:38:00' in html

    def test_start_and_end_times_shown(self):
        html = self._gen(_log_data())
        assert '10:37:00' in html
        assert '10:39:00' in html


# ── profile_page ──────────────────────────────────────────────────────────────

class TestProfilePage:
    def _gen(self):
        from tacek.html.profile_page import generate
        return generate()

    def test_valid_html(self):
        html = self._gen()
        assert html.startswith('<!DOCTYPE html>')
        assert '</html>' in html

    def test_fodmap_preference_buttons(self):
        html = self._gen()
        assert 'setFodmapPref' in html
        assert 'Nízký' in html
        assert 'Střední' in html

    def test_fitness_preference_buttons(self):
        html = self._gen()
        assert 'setFitnessPref' in html
        assert 'Dobré' in html
        assert 'Výborné' in html

    def test_back_link_to_index(self):
        assert 'index.html' in self._gen()

    def test_saved_message_element(self):
        assert 'savedMsg' in self._gen()
