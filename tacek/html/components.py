import re
from datetime import datetime
from tacek.html.assets import DARK_INIT, TAILWIND, CHIP_CSS

FODMAP_CZ  = {'Low': 'Nízký', 'Moderate': 'Střední', 'High': 'Vysoký'}
FITNESS_CZ = {'Low': 'Slabé', 'Medium': 'Dobré', 'High': 'Výborné'}


def fodmap_badge(level):
    return {
        'Low':      'border border-green-300 text-green-600 dark:border-green-700 dark:text-green-400',
        'Moderate': 'border border-amber-300 text-amber-600 dark:border-amber-700 dark:text-amber-400',
        'High':     'border border-red-300   text-red-600   dark:border-red-700   dark:text-red-400',
    }.get(level, 'border border-gray-200 text-gray-500 dark:border-gray-600 dark:text-gray-400')


def fitness_badge(level):
    return {
        'High':   'border border-green-300 text-green-600 dark:border-green-700 dark:text-green-400',
        'Medium': 'border border-amber-300 text-amber-600 dark:border-amber-700 dark:text-amber-400',
        'Low':    'border border-red-300   text-red-600   dark:border-red-700   dark:text-red-400',
    }.get(level, 'border border-gray-200 text-gray-500 dark:border-gray-600 dark:text-gray-400')


def stars_to_level(stars):
    s = int(stars) if stars else 0
    return 'High' if s >= 4 else ('Medium' if s >= 3 else 'Low')


def parse_date(label):
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
    return None


def head(title, extra_css=''):
    return f"""<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  {DARK_INIT}
  {TAILWIND}
  {extra_css}
</head>"""


def header(back_href, back_label, title, right_link_href=None, right_link_text=None):
    right = ''
    if right_link_href:
        right = f'<a href="{right_link_href}" target="_blank" class="text-xs text-gray-400 dark:text-gray-500 hover:text-green-600 dark:hover:text-green-400 hidden sm:block">{right_link_text}</a>'
    return f"""
  <header class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700 sticky top-0 z-10">
    <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-3 min-w-0">
        <a href="{back_href}" class="text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300 text-sm font-medium shrink-0">&larr; {back_label}</a>
        <span class="text-gray-200 dark:text-gray-600">|</span>
        <span class="font-semibold text-gray-800 dark:text-gray-100 text-sm truncate">{title}</span>
      </div>
      <div class="flex items-center gap-1 shrink-0">
        {right}
        <a href="profile.html" class="w-8 h-8 flex items-center justify-center rounded-full text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-base" title="Nastavení">&#9881;</a>
        <button id="themeBtn" class="w-8 h-8 flex items-center justify-center rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" title="Přepnout motiv"></button>
      </div>
    </div>
  </header>"""
