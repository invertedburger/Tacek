import re
from datetime import datetime

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
    m = re.search(r'(\d{1,2})[.\s]+(\d{1,2})[.\s]+(\d{4})', str(label))
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None


def _stars_to_level(stars):
    s = int(stars) if stars else 0
    return 'High' if s >= 4 else ('Medium' if s >= 3 else 'Low')


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

    pool = [d for d in scored if d['today']] or scored
    pool.sort(key=lambda d: d['score'], reverse=True)
    seen, result = set(), []
    for d in pool:
        if d['name'] not in seen and len(result) < n:
            seen.add(d['name'])
            result.append(d)
    return result
