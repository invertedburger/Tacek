import re
from datetime import datetime, timedelta

# Czech/English weekday names → Python weekday index (Mon=0 … Sun=6).
_WEEKDAYS = {
    'pondělí': 0, 'pondeli': 0, 'monday': 0,
    'úterý': 1, 'utery': 1, 'tuesday': 1,
    'středa': 2, 'streda': 2, 'wednesday': 2,
    'čtvrtek': 3, 'ctvrtek': 3, 'thursday': 3,
    'pátek': 4, 'patek': 4, 'friday': 4,
    'sobota': 5, 'saturday': 5,
    'neděle': 6, 'nedele': 6, 'sunday': 6,
}


def _weekday_date(label):
    """Resolve a weekday name (no explicit date) to its date in the current week.

    Menus posted as images (e.g. U Tesaře) label days only by name, with no
    number. Mapping the name to this week's matching calendar date lets the rest
    of the pipeline treat the day exactly like a dated one, so a weekly menu
    shows only today's dishes instead of pooling the whole week as "today".
    """
    low = str(label).lower()
    for name, dow in _WEEKDAYS.items():
        if name in low:
            monday = datetime.now() - timedelta(days=datetime.now().weekday())
            return (monday + timedelta(days=dow)).strftime('%Y-%m-%d')
    return None


_FODMAP_SCORE  = {'Low': 3, 'Moderate': 2, 'High': 1}
_FITNESS_SCORE = {'High': 3, 'Medium': 2, 'Low': 1}

_EXCLUDE = (
    'polévka', 'polevka', 'soup',
    'salát', 'salat', 'salad',
    'předkrm', 'predkrm', 'starter',
    'dezert', 'dessert',
    'vývar', 'vyvar',
    'pomazánka', 'pomazanka',
    'krém', 'krem',
)


def _is_main_dish(name):
    low = name.lower()
    return not any(kw in low for kw in _EXCLUDE)


def _clean_name(name):
    return re.sub(r'^[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]+\s*:\s*', '', name).strip()


def _parse_date(label):
    label = str(label)
    m = re.search(r'(\d{1,2})[.\s]+(\d{1,2})[.\s]+(\d{4})', label)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).strftime('%Y-%m-%d')
        except ValueError:
            pass
    m = re.search(r'(\d{1,2})\.\s*(\d{1,2})\.', label)
    if m:
        try:
            return datetime(datetime.now().year, int(m.group(2)), int(m.group(1))).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return _weekday_date(label)


def _stars_to_level(stars):
    s = int(stars) if stars else 0
    return 'High' if s >= 4 else ('Medium' if s >= 3 else 'Low')


def has_today_menu(data):
    today = datetime.now().strftime('%Y-%m-%d')
    for day in data.get('days', []):
        date_str = _parse_date(day.get('day', ''))
        if not date_str or date_str == today:
            return True
    return False


def recommend_date(data):
    """Date label (YYYY-MM-DD) the top dishes belong to, for client-side gating.

    Returns the matched date if a dated day equals today, '' if today's menu is
    undated (so it should always show), or None when there is no today menu.
    Mirrors the today-pool logic in get_top_dishes so the index gate agrees with
    the menu page's per-day data-date filtering instead of the build timestamp.
    """
    today = datetime.now().strftime('%Y-%m-%d')
    has_undated = False
    for day in data.get('days', []):
        date_str = _parse_date(day.get('day', ''))
        if date_str == today:
            return today
        if not date_str:
            has_undated = True
    return '' if has_undated else None


def get_top_dishes(data, n=3):
    today = datetime.now().strftime('%Y-%m-%d')
    scored = []
    for day in data.get('days', []):
        date_str = _parse_date(day.get('day', ''))
        is_today = not date_str or date_str == today
        for dish in day.get('dishes', []):
            name = _clean_name(dish.get('name', ''))
            if not _is_main_dish(name):
                continue
            fodmap  = dish.get('fodmap_level', 'Moderate')
            fitness = dish.get('fitness_level') or _stars_to_level(dish.get('fitness_stars', 0))
            if fodmap == 'High' and fitness == 'Low':
                continue
            score = _FODMAP_SCORE.get(fodmap, 2) + _FITNESS_SCORE.get(fitness, 2)
            scored.append({'name': name, 'fodmap': fodmap, 'fitness': fitness, 'score': score, 'today': is_today})

    pool = [d for d in scored if d['today']]
    if not pool:
        return []
    pool.sort(key=lambda d: d['score'], reverse=True)
    seen, result = set(), []
    for d in pool:
        if d['name'] not in seen and len(result) < n:
            seen.add(d['name'])
            result.append(d)
    return result
