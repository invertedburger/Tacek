from tacek.html.assets import CHIP_CSS, THEME_JS, PROFILE_JS, LANG_JS
from tacek.html.components import head, header
from tacek.html import i18n


def generate():
    hdr = header('index.html', i18n.cs('nav.back'), i18n.cs('profile.title'))
    return f"""<!DOCTYPE html>
<html lang="cs">
{head("Nastavení &ndash; Tácek", CHIP_CSS)}
<body class="bg-gray-50 dark:bg-gray-900 min-h-screen">
{hdr}

  <main class="max-w-2xl mx-auto px-4 py-8">
    <div class="mb-6">
      <h1 class="text-xl font-bold text-gray-800 dark:text-gray-100" data-i18n="profile.heading">{i18n.cs('profile.heading')}</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1" data-i18n="profile.sub">{i18n.cs('profile.sub')}</p>
    </div>

    <div class="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-5 mb-4">
      <h2 class="font-semibold text-gray-800 dark:text-gray-100 mb-1" data-i18n="profile.fodmap">{i18n.cs('profile.fodmap')}</h2>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-3" data-i18n="profile.fodmap_sub">{i18n.cs('profile.fodmap_sub')}</p>
      <div class="flex flex-wrap gap-2">
        <button onclick="setFodmapPref('all')"      data-pref-filter="fodmap" data-value="all"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border" data-i18n="filter.all">{i18n.cs('filter.all')}</button>
        <button onclick="setFodmapPref('Low')"      data-pref-filter="fodmap" data-value="Low"      data-color="green"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border" data-i18n="fodmap.Low">{i18n.cs('fodmap.Low')}</button>
        <button onclick="setFodmapPref('Moderate')" data-pref-filter="fodmap" data-value="Moderate" data-color="amber"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border" data-i18n="fodmap.Moderate">{i18n.cs('fodmap.Moderate')}</button>
      </div>
    </div>

    <div class="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-5 mb-4">
      <h2 class="font-semibold text-gray-800 dark:text-gray-100 mb-1" data-i18n="profile.fitness">{i18n.cs('profile.fitness')}</h2>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-3" data-i18n="profile.fitness_sub">{i18n.cs('profile.fitness_sub')}</p>
      <div class="flex flex-wrap gap-2">
        <button onclick="setFitnessPref('all')"    data-pref-filter="fitness" data-value="all"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border" data-i18n="filter.all">{i18n.cs('filter.all')}</button>
        <button onclick="setFitnessPref('Medium')" data-pref-filter="fitness" data-value="Medium" data-color="amber"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border" data-i18n="fitness.Medium">{i18n.cs('fitness.Medium')}</button>
        <button onclick="setFitnessPref('High')"   data-pref-filter="fitness" data-value="High"   data-color="green"
          class="chip-inactive px-3 py-1.5 rounded-full text-sm font-medium border" data-i18n="fitness.High">{i18n.cs('fitness.High')}</button>
      </div>
    </div>

    <div id="savedMsg" class="hidden text-center text-green-600 dark:text-green-400 text-sm font-medium py-2" data-i18n="profile.saved">
      {i18n.cs('profile.saved')}
    </div>
  </main>

  <footer class="text-center text-gray-300 dark:text-gray-600 text-xs py-8">
    Tácek
  </footer>

  <script>
    {THEME_JS}
    const PAGE_TITLE_KEY = "title.profile";
    {LANG_JS}
    {PROFILE_JS}
  </script>
</body>
</html>"""
