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


_DATE_RE = re.compile(r'(\d{1,2})[.\s]+(\d{1,2})(?:[.\s]+(\d{4}))?')


def _weekday_index(label):
    """Weekday index of the first weekday name in the label, or None."""
    low = str(label).lower()
    hits = [(low.index(name), dow) for name, dow in _WEEKDAYS.items() if name in low]
    return min(hits)[1] if hits else None


def _all_dates(label):
    """Every valid date in the label, in order. A year stated once applies to all.

    Weekly menus label a day with the whole week's range ("Pondělí 14. 9. -
    18. 9. 2026"), where only the last date carries the year.
    """
    raw = [(int(m.group(1)), int(m.group(2)), m.group(3)) for m in _DATE_RE.finditer(str(label))]
    year = next((int(y) for _, _, y in raw if y), datetime.now().year)
    dates = []
    for day, month, y in raw:
        try:
            dates.append(datetime(int(y) if y else year, month, day))
        except ValueError:
            pass
    # A range over New Year ("29. 12. - 2. 1. 2027") states only the later year,
    # so an inherited year would push the start of the week a year forward.
    for i in range(len(dates) - 2, -1, -1):
        if dates[i] > dates[i + 1]:
            dates[i] = dates[i].replace(year=dates[i].year - 1)
    return dates


def _parse_date(label):
    label = str(label)
    dates = _all_dates(label)
    if len(dates) > 1:
        # A date range covers the whole week, so the weekday name — not the
        # range itself — says which day this entry is. Without it every day of
        # the menu would collapse onto the same date.
        dow = _weekday_index(label)
        if dow is not None:
            for d in dates:
                if d.weekday() == dow:
                    return d.strftime('%Y-%m-%d')
            monday = dates[0] - timedelta(days=dates[0].weekday())
            return (monday + timedelta(days=dow)).strftime('%Y-%m-%d')
    if dates:
        return dates[0].strftime('%Y-%m-%d')
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


def menu_dates(data):
    """Every date the menu carries, as a set. Undated days appear as ''.

    Lets the index tell "this card has a menu for today" apart from "this card
    has *recommendations* for today" — a day of nothing but soups has the former
    and not the latter.
    """
    return {_parse_date(day.get('day', '')) or '' for day in data.get('days', [])}


def _score_dish(dish):
    """Scored entry for one dish, or None when it isn't recommendable."""
    name = _clean_name(dish.get('name', ''))
    if not _is_main_dish(name):
        return None
    fodmap  = dish.get('fodmap_level', 'Moderate')
    fitness = dish.get('fitness_level') or _stars_to_level(dish.get('fitness_stars', 0))
    if fodmap == 'High' and fitness == 'Low':
        return None
    return {
        'name': name, 'fodmap': fodmap, 'fitness': fitness,
        'score': _FODMAP_SCORE.get(fodmap, 2) + _FITNESS_SCORE.get(fitness, 2),
    }


def _top_of(dishes, n):
    scored = [s for s in (_score_dish(d) for d in dishes) if s]
    scored.sort(key=lambda d: d['score'], reverse=True)
    seen, result = set(), []
    for d in scored:
        if d['name'] not in seen and len(result) < n:
            seen.add(d['name'])
            result.append(d)
    return result


def get_top_dishes_by_day(data, n=3):
    """Top dishes for *every* day in the menu, keyed by date ('' when undated).

    A weekly menu is analyzed in full by a single run, so handing the index every
    day lets a card show the right day's picks before that day's build has fired
    — instead of sitting on the build day's picks until the next trigger.
    """
    buckets = {}
    for day in data.get('days', []):
        key = _parse_date(day.get('day', '')) or ''
        buckets.setdefault(key, []).extend(day.get('dishes', []))
    return {k: top for k, top in ((k, _top_of(d, n)) for k, d in buckets.items()) if top}


def get_top_dishes(data, n=3):
    by_day = get_top_dishes_by_day(data, n)
    return by_day.get(datetime.now().strftime('%Y-%m-%d')) or by_day.get('', [])
