from tacek.html.assets import CHIP_CSS, THEME_JS, PROFILE_JS
from tacek.html.components import head, header


def generate():
    hdr = header('index.html', 'Zpět', 'Nastavení')
    return f"""<!DOCTYPE html>
<html lang="cs">
{head("Nastavení &ndash; Tácek", CHIP_CSS)}
<body class="bg-gray-50 dark:bg-gray-900 min-h-screen">
{hdr}

  <main class="max-w-2xl mx-auto px-4 py-8">
    <div class="mb-6">
      <h1 class="text-xl font-bold text-gray-800 dark:text-gray-100">Dietní preference</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Uloženo lokálně &middot; Automaticky aplikováno na stránkách menu</p>
    </div>

    <div class="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-5 mb-4">
      <h2 class="font-semibold text-gray-800 dark:text-gray-100 mb-1">FODMAP filtr</h2>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">Výchozí filtr při otevření menu</p>
      <div class="flex flex-wrap gap-2">
        <button onclick="setFodmapPref('all')"      data-pref-filter="fodmap" data-value="all"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border">Vše</button>
        <button onclick="setFodmapPref('Low')"      data-pref-filter="fodmap" data-value="Low"      data-color="green"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border">Nízký</button>
        <button onclick="setFodmapPref('Moderate')" data-pref-filter="fodmap" data-value="Moderate" data-color="amber"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border">Střední</button>
        <button onclick="setFodmapPref('High')"     data-pref-filter="fodmap" data-value="High"     data-color="red"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border">Vysoký</button>
      </div>
    </div>

    <div class="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-5 mb-4">
      <h2 class="font-semibold text-gray-800 dark:text-gray-100 mb-1">Fitness úroveň</h2>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">Zobrazit pouze pokrmy s tímto fitness hodnocením</p>
      <div class="flex flex-wrap gap-2">
        <button onclick="setFitnessPref('all')"    data-pref-filter="fitness" data-value="all"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border">Vše</button>
        <button onclick="setFitnessPref('Low')"    data-pref-filter="fitness" data-value="Low"    data-color="red"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border">Slabé</button>
        <button onclick="setFitnessPref('Medium')" data-pref-filter="fitness" data-value="Medium" data-color="amber"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border">Dobré</button>
        <button onclick="setFitnessPref('High')"   data-pref-filter="fitness" data-value="High"   data-color="green"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border">Výborné</button>
      </div>
    </div>

    <div id="savedMsg" class="hidden text-center text-green-600 dark:text-green-400 text-sm font-medium py-2">
      &#10003; Preference uloženy
    </div>
  </main>

  <footer class="text-center text-gray-300 dark:text-gray-600 text-xs py-8">
    Tácek
  </footer>

  <script>
    {THEME_JS}
    {PROFILE_JS}
  </script>
</body>
</html>"""
