from urllib.parse import quote_plus
from tacek.html.assets import CHIP_CSS, THEME_JS
from tacek.html.components import head, fodmap_badge, fitness_badge, FODMAP_CZ, FITNESS_CZ


def generate(sources, timestamp):
    cards_html = ''
    for i, src in enumerate(sources):
        name         = src['name']
        url          = src['url']
        result_file  = src['result_file']
        last_updated = src.get('last_updated', timestamp)
        top_dishes   = src.get('top_dishes', [])

        rows = ''
        for d in top_dishes:
            dn   = d['name'].capitalize() if d['name'] == d['name'].upper() else d['name']
            fl   = FODMAP_CZ.get(d['fodmap'], d['fodmap'])
            fit  = FITNESS_CZ.get(d['fitness'], d['fitness'])
            rows += f"""
            <div class="flex items-center gap-2 py-1.5 border-b border-gray-50 dark:border-gray-700/60 last:border-0">
              <a href="https://www.google.com/search?tbm=isch&q={quote_plus(d['name'])}" target="_blank" rel="noopener"
                 class="flex-1 text-sm text-gray-700 dark:text-gray-200 truncate hover:text-green-600 dark:hover:text-green-400 transition-colors">{dn}</a>
              <span class="shrink-0 w-[4.5rem] text-center px-1.5 py-0.5 rounded text-xs font-medium {fodmap_badge(d['fodmap'])}">{fl}</span>
              <span class="shrink-0 w-[4.5rem] text-center px-1.5 py-0.5 rounded text-xs font-medium {fitness_badge(d['fitness'])}">{fit}</span>
            </div>"""

        col_headers = """
            <div class="flex items-center gap-2 pb-1 mb-0.5">
              <span class="flex-1"></span>
              <span class="shrink-0 w-[4.5rem] text-center text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">FODMAP</span>
              <span class="shrink-0 w-[4.5rem] text-center text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">Fitness</span>
            </div>""" if rows else ''

        dishes_section = f"""
          <div class="px-5 py-3 border-t border-gray-100 dark:border-gray-700">
            <p class="text-xs font-medium text-gray-400 dark:text-gray-500 mb-1.5">Doporučujeme dnes</p>
            {col_headers}
            {rows}
          </div>""" if rows else ''

        cards_html += f"""
      <div class="anim-card card-hover bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 flex flex-col" style="animation-delay:{i * 80}ms">
        <div class="px-5 pt-5 pb-4 flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="font-semibold text-gray-800 dark:text-gray-100 leading-tight">{name}</h3>
            <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">Aktualizováno: {last_updated}</p>
          </div>
          <a href="{url}" target="_blank"
             class="shrink-0 text-xs text-gray-400 dark:text-gray-500 hover:text-green-600 dark:hover:text-green-400 mt-0.5">
            originál &nearr;
          </a>
        </div>
        {dishes_section}
        <div class="px-5 py-4 mt-auto">
          <a href="{result_file}"
             class="block text-center bg-green-600 hover:bg-green-700 dark:bg-green-800 dark:hover:bg-green-700 text-white py-2 rounded-lg text-sm font-medium transition-colors">
            Zobrazit celé menu &rarr;
          </a>
        </div>
      </div>"""

    with_coords = [s for s in sources if s.get('coords')]
    if with_coords:
        markers_js = ','.join(
            f'{{"n":"{s["name"]}","u":"{s["result_file"]}","lat":{s["coords"][0]},"lng":{s["coords"][1]}}}'
            for s in with_coords
        )
        leaflet_css = '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>'
        map_section = """
  <div class="max-w-2xl mx-auto px-4 pb-6">
    <h2 class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">Mapa</h2>
    <div id="map" class="rounded-xl overflow-hidden border border-gray-100 dark:border-gray-700" style="height:300px"></div>
  </div>"""
        map_script = f"""
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
  (function() {{
    const lt = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{attribution:'&copy; OSM &copy; CARTO',maxZoom:19}});
    const dt = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{attribution:'&copy; OSM &copy; CARTO',maxZoom:19}});
    const map = L.map('map');
    let tile = document.documentElement.classList.contains('dark') ? dt : lt;
    tile.addTo(map);
    new MutationObserver(() => {{
      const nd = document.documentElement.classList.contains('dark');
      map.removeLayer(tile); tile = nd ? dt : lt; tile.addTo(map);
    }}).observe(document.documentElement, {{attributes:true, attributeFilter:['class']}});
    const icon = L.divIcon({{
      className: '',
      html: '<div style="background:#22c55e;color:#fff;border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;font-size:18px;box-shadow:0 2px 8px rgba(0,0,0,.3)">&#127860;</div>',
      iconSize:[34,34], iconAnchor:[17,17], popupAnchor:[0,-20]
    }});
    const rs = [{markers_js}];
    rs.forEach(r => L.marker([r.lat,r.lng],{{icon}}).addTo(map)
      .bindPopup('<b style="font-size:13px">'+r.n+'</b><br><a href="'+r.u+'" style="color:#22c55e;font-size:12px">Zobrazit menu &rarr;</a>'));
    if (rs.length) map.fitBounds(rs.map(r=>[r.lat,r.lng]),{{padding:[50,50]}});
  }})();
  </script>"""
    else:
        leaflet_css = ''
        map_section = ''
        map_script  = ''

    return f"""<!DOCTYPE html>
<html lang="cs">
{head("Tácek &ndash; Restaurace", leaflet_css + CHIP_CSS)}
<body class="bg-gray-50 dark:bg-gray-900 min-h-screen">

  <header class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700">
    <div class="max-w-2xl mx-auto px-4 py-5 flex items-center justify-between">
      <div>
        <div class="flex items-baseline gap-2">
          <h1 class="text-2xl font-bold text-green-600 logo-glow">Tácek</h1>
          <span class="text-gray-400 dark:text-gray-500 text-sm font-medium">Holandsk&aacute;, Brno</span>
        </div>
        <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">Ob&#283;dy v okol&iacute; Holandsk&eacute; &middot; FODMAP &amp; v&yacute;&#382;iva</p>
      </div>
      <div class="flex items-center gap-1">
        <a href="profile.html" class="w-8 h-8 flex items-center justify-center rounded-full text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-base" title="Nastavení">&#9881;</a>
        <button id="themeBtn" class="w-8 h-8 flex items-center justify-center rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" title="Přepnout motiv"></button>
      </div>
    </div>
  </header>

  <main class="max-w-2xl mx-auto px-4 py-8">
    <div class="grid grid-cols-2 gap-3 mb-6">
      <div class="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-4">
        <span class="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400">FODMAP</span>
        <p class="text-xs text-gray-500 dark:text-gray-400 leading-relaxed mt-1">
          Hodnotí, jak je jídlo vhodné pro citlivý žaludek. Nízký FODMAP = lepší volba.
        </p>
        <div class="flex gap-1.5 mt-2.5 flex-wrap">
          <span class="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400">Nízký = vhodné</span>
          <span class="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400">Vysoký = riziko</span>
        </div>
      </div>
      <div class="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-4">
        <span class="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400">Fitness</span>
        <p class="text-xs text-gray-500 dark:text-gray-400 leading-relaxed mt-1">
          Celková výživová hodnota jídla &ndash; obsah bílkovin, kalorií a složení makronutrientů.
        </p>
        <div class="flex gap-1.5 mt-2.5 flex-wrap">
          <span class="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400">Výborné = zdravé</span>
          <span class="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400">Slabé = méně vhodné</span>
        </div>
      </div>
    </div>

    <h2 class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-4">Restaurace</h2>
    <div class="flex flex-col gap-3">
      {cards_html}
    </div>
  </main>
{map_section}
  <footer class="text-center text-gray-300 dark:text-gray-600 text-xs py-8">
    Aktualizováno: {timestamp} &middot; Tácek &amp; Google Gemini
  </footer>

  <script>
    {THEME_JS}
  </script>
{map_script}
</body>
</html>"""
