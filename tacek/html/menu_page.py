from urllib.parse import quote_plus
from tacek.html.assets import CHIP_CSS, THEME_JS, FILTER_JS
from tacek.html.components import (
    head, header, fodmap_badge, fitness_badge,
    stars_to_level, parse_date, FODMAP_CZ, FITNESS_CZ,
)


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
                  <span class="px-2 py-0.5 rounded-full text-xs font-medium {fodmap_badge(fodmap)}">{fodmap_label} FODMAP</span>
                  <span class="px-2 py-0.5 rounded-full text-xs font-medium {fitness_badge(fitness)}">{fitness_label} fitness</span>
                </div>
                {ing_html}
              </div>
              <div class="text-right shrink-0">
                <div class="font-bold text-gray-800 dark:text-gray-100 text-sm">{calories} kcal</div>
                <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{protein}g bílkovin</div>
                <div class="text-xs text-gray-400 dark:text-gray-500">{carbs}g S &middot; {fat}g T</div>
              </div>
            </div>
          </a>"""

        date_str = parse_date(day_label)
        date_attr = f'data-date="{date_str}"' if date_str else 'data-date=""'
        days_html += f"""
        <div class="mb-8" {date_attr}>
          <h3 class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3 px-1">{day_label}</h3>
          {dishes_html}
        </div>"""

    hdr = header('index.html', 'Zpět', restaurant_name,
                 right_link_href=source_url, right_link_text='Originál &nearr;')

    return f"""<!DOCTYPE html>
<html lang="cs">
{head(f"{restaurant_name} &ndash; Tácek", CHIP_CSS)}
<body class="bg-gray-50 dark:bg-gray-900 min-h-screen">
{hdr}

  <div class="max-w-2xl mx-auto px-4 py-6">
    <div class="mb-5">
      <h1 class="text-xl font-bold text-gray-800 dark:text-gray-100">Analyzované menu</h1>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">Analýza AI &middot; Google Gemini</p>
    </div>

    <div class="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-3 mb-4">
      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-1.5">
          <span class="text-xs font-medium text-gray-500 dark:text-gray-400 w-14 shrink-0">FODMAP</span>
          <div class="flex gap-1">
            <button onclick="setFodmapFilter('all')"      data-filter="fodmap" data-value="all"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border">Vše</button>
            <button onclick="setFodmapFilter('High')"     data-filter="fodmap" data-value="High"     data-color="red"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border">Vysoký</button>
            <button onclick="setFodmapFilter('Moderate')" data-filter="fodmap" data-value="Moderate" data-color="amber"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border">Střední</button>
            <button onclick="setFodmapFilter('Low')"      data-filter="fodmap" data-value="Low"      data-color="green"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border">Nízký</button>
          </div>
        </div>
        <div class="flex items-center gap-1.5">
          <span class="text-xs font-medium text-gray-500 dark:text-gray-400 w-14 shrink-0">Fitness</span>
          <div class="flex gap-1">
            <button onclick="setFitnessFilter('all')"    data-filter="fitness" data-value="all"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border">Vše</button>
            <button onclick="setFitnessFilter('Low')"    data-filter="fitness" data-value="Low"    data-color="red"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border">Slabé</button>
            <button onclick="setFitnessFilter('Medium')" data-filter="fitness" data-value="Medium" data-color="amber"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border">Dobré</button>
            <button onclick="setFitnessFilter('High')"   data-filter="fitness" data-value="High"   data-color="green"
              class="chip-inactive px-2.5 py-1 rounded-full text-xs font-medium border">Výborné</button>
          </div>
        </div>
      </div>
    </div>

    <div class="flex items-center justify-between mb-4">
      <span class="text-xs text-gray-400 dark:text-gray-500">Zobrazeno: dnes</span>
      <button id="todayBtn" onclick="toggleToday()"
        class="text-xs text-green-600 dark:text-green-500 hover:underline">Zobrazit celý týden</button>
    </div>
    <div id="noToday" class="hidden text-center text-gray-400 dark:text-gray-500 py-10 text-sm">
      Dnes žádné menu&nbsp;&mdash; zkuste <button onclick="toggleToday()" class="underline">zobrazit celý týden</button>.
    </div>

    {days_html}
  </div>

  <footer class="text-center text-gray-300 dark:text-gray-600 text-xs py-8">
    Aktualizováno: {last_updated} &middot; Tácek
  </footer>

  <script>
    {THEME_JS}
    {FILTER_JS}
  </script>
</body>
</html>"""
