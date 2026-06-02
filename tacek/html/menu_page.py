from urllib.parse import quote_plus
from tacek.html.assets import CHIP_CSS, THEME_JS, FILTER_JS, LANG_JS
from tacek.html.components import (
    head, header, fodmap_badge, fitness_badge,
    stars_to_level, parse_date, FODMAP_CZ, FITNESS_CZ,
)
from tacek.html import i18n


def generate(data, restaurant_name, source_url, last_updated):
    days_html = ''
    for day_data in data.get('days', []):
        day_label = day_data.get('day', '')
        dishes_html = ''
        for i, dish in enumerate(day_data.get('dishes', [])):
            name          = dish.get('name', '')
            fodmap        = dish.get('fodmap_level', 'Moderate')
            fitness       = dish.get('fitness_level') or stars_to_level(dish.get('fitness_stars', 0))
            ingredients   = ', '.join(dish.get('problematic_ingredients', []))
            protein       = dish.get('protein_g', '?')
            carbs         = dish.get('carbs_g', '?')
            fat           = dish.get('fat_g', '?')
            calories      = dish.get('calories_kcal', '?')
            fodmap_label  = FODMAP_CZ.get(fodmap, fodmap)
            fitness_label = FITNESS_CZ.get(fitness, fitness)
            ing_html = f'<p class="text-xs text-gray-400 dark:text-gray-500 mt-1.5">{ingredients}</p>' if ingredients else ''
            dishes_html += f"""
          <a href="https://www.google.com/search?tbm=isch&q={quote_plus(name)}" target="_blank" rel="noopener"
             class="anim-card card-hover block bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 mb-3" style="animation-delay:{i * 60}ms" data-fodmap="{fodmap}" data-fitness="{fitness}">
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <p class="font-semibold text-gray-800 dark:text-gray-100 text-sm leading-snug">{name}</p>
                <div class="flex flex-wrap items-center gap-2 mt-2">
                  <span class="px-2 py-0.5 rounded-full text-xs font-medium {fodmap_badge(fodmap)}"><span data-i18n="fodmap.{fodmap}">{fodmap_label}</span> FODMAP</span>
                  <span class="px-2 py-0.5 rounded-full text-xs font-medium {fitness_badge(fitness)}"><span data-i18n="fitness.{fitness}">{fitness_label}</span> fitness</span>
                </div>
                {ing_html}
              </div>
              <div class="text-right shrink-0">
                <div class="font-bold text-gray-800 dark:text-gray-100 text-sm">{calories} kcal</div>
                <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{protein}g <span data-i18n="nutrition.protein">{i18n.cs('nutrition.protein')}</span></div>
                <div class="text-xs text-gray-400 dark:text-gray-500">{carbs}g <span data-i18n="nutrition.carbs">S</span> &middot; {fat}g <span data-i18n="nutrition.fat">T</span></div>
              </div>
            </div>
          </a>"""

        date_str = parse_date(day_label)
        date_attr = f'data-date="{date_str}"' if date_str else 'data-date=""'
        days_html += f"""
        <div class="mb-8" {date_attr}>
          <h3 class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3 px-1" data-weekday>{day_label}</h3>
          {dishes_html}
        </div>"""

    hdr = header('index.html', i18n.cs('nav.back'), restaurant_name,
                 right_link_href=source_url, right_link_text=i18n.cs('nav.original'))

    return f"""<!DOCTYPE html>
<html lang="cs">
{head(f"{restaurant_name} &ndash; Tácek", CHIP_CSS)}
<body class="bg-gray-50 dark:bg-gray-900 min-h-screen">
{hdr}

  <div class="max-w-2xl mx-auto px-4 py-6">
    <div class="mb-5">
      <h1 class="text-xl font-bold text-gray-800 dark:text-gray-100" data-i18n="menu.heading">{i18n.cs('menu.heading')}</h1>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5" data-i18n="menu.subheading">{i18n.cs('menu.subheading')}</p>
    </div>

    <div class="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-3 mb-4">
      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-1.5">
          <span class="text-xs font-medium text-gray-500 dark:text-gray-400 w-14 shrink-0">FODMAP</span>
          <div class="flex gap-1">
            <button onclick="setFodmapFilter('all')"      data-filter="fodmap" data-value="all"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border" data-i18n="filter.all">{i18n.cs('filter.all')}</button>
            <button onclick="setFodmapFilter('Moderate')" data-filter="fodmap" data-value="Moderate" data-color="amber"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border" data-i18n="fodmap.Moderate">{i18n.cs('fodmap.Moderate')}</button>
            <button onclick="setFodmapFilter('Low')"      data-filter="fodmap" data-value="Low"      data-color="green"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border" data-i18n="fodmap.Low">{i18n.cs('fodmap.Low')}</button>
          </div>
        </div>
        <div class="flex items-center gap-1.5">
          <span class="text-xs font-medium text-gray-500 dark:text-gray-400 w-14 shrink-0">Fitness</span>
          <div class="flex gap-1">
            <button onclick="setFitnessFilter('all')"    data-filter="fitness" data-value="all"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border" data-i18n="filter.all">{i18n.cs('filter.all')}</button>
            <button onclick="setFitnessFilter('Medium')" data-filter="fitness" data-value="Medium" data-color="amber"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border" data-i18n="fitness.Medium">{i18n.cs('fitness.Medium')}</button>
            <button onclick="setFitnessFilter('High')"   data-filter="fitness" data-value="High"   data-color="green"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border" data-i18n="fitness.High">{i18n.cs('fitness.High')}</button>
          </div>
        </div>
      </div>
    </div>

    <div class="flex items-center justify-between mb-4">
      <span class="text-xs text-gray-400 dark:text-gray-500" data-i18n="menu.showing_today">{i18n.cs('menu.showing_today')}</span>
      <button id="todayBtn" onclick="toggleToday()"
        class="text-xs text-green-600 dark:text-green-500 hover:underline" data-i18n="week.show">{i18n.cs('week.show')}</button>
    </div>
    <div id="noToday" class="hidden text-center text-gray-400 dark:text-gray-500 py-10 text-sm">
      <span data-i18n="menu.none_today">{i18n.cs('menu.none_today')}</span><button onclick="toggleToday()" class="underline" data-i18n="menu.none_today_link">{i18n.cs('menu.none_today_link')}</button>.
    </div>

    {days_html}
  </div>

  <footer class="text-center text-gray-300 dark:text-gray-600 text-xs py-8">
    <span data-i18n="card.updated">{i18n.cs('card.updated')}</span> {last_updated} &middot; Tácek
  </footer>

  <script>
    {THEME_JS}
    {FILTER_JS}
    {LANG_JS}
  </script>
</body>
</html>"""
