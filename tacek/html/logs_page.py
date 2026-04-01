from datetime import datetime
from tacek.html.assets import CHIP_CSS, THEME_JS
from tacek.html.components import head


def generate(log_data):
    """Generate HTML for the run logs page."""
    if not log_data:
        return f"""<!DOCTYPE html>
<html lang="cs">
{head("Tácek – Logy", CHIP_CSS)}
<body class="bg-gray-50 dark:bg-gray-900 min-h-screen">
  <header class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700">
    <div class="max-w-4xl mx-auto px-4 py-5 flex items-center justify-between">
      <div>
        <div class="flex items-baseline gap-2">
          <h1 class="text-2xl font-bold text-green-600 logo-glow">Tácek</h1>
          <span class="text-gray-400 dark:text-gray-500 text-sm font-medium">Logy</span>
        </div>
      </div>
      <a href="index.html" class="text-xs text-gray-400 dark:text-gray-500 hover:text-green-600 dark:hover:text-green-400">
        &larr; Zpět
      </a>
    </div>
  </header>
  <main class="max-w-4xl mx-auto px-4 py-8">
    <p class="text-gray-500 dark:text-gray-400">Žádné logy k dispozici</p>
  </main>
  <script>
    {THEME_JS}
  </script>
</body>
</html>"""

    start_time = log_data.get('start_time', '')
    end_time = log_data.get('end_time', '')
    logs = log_data.get('logs', [])

    # Format timestamps
    try:
        start_dt = datetime.fromisoformat(start_time).strftime('%Y-%m-%d %H:%M:%S')
        end_dt = datetime.fromisoformat(end_time).strftime('%Y-%m-%d %H:%M:%S')
    except:
        start_dt = start_time
        end_dt = end_time

    # Build log entries HTML
    logs_html = ''
    for log_entry in logs:
        msg = log_entry.get('message', '')
        try:
            entry_time = datetime.fromisoformat(log_entry.get('time', '')).strftime('%H:%M:%S')
        except:
            entry_time = log_entry.get('time', '')

        # Color code messages
        if 'Analyzing' in msg or 'analyzing' in msg:
            color_class = 'text-blue-600 dark:text-blue-400'
        elif 'No change' in msg:
            color_class = 'text-gray-600 dark:text-gray-400'
        elif 'WARNING' in msg or 'ERROR' in msg or 'error' in msg or 'failed' in msg or 'Failed' in msg:
            color_class = 'text-red-600 dark:text-red-400'
        elif 'Saved' in msg or 'written' in msg or 'Index page' in msg:
            color_class = 'text-green-600 dark:text-green-400'
        else:
            color_class = 'text-gray-700 dark:text-gray-300'

        logs_html += f"""
    <div class="py-2 border-b border-gray-200 dark:border-gray-700 last:border-0">
      <span class="text-xs text-gray-400 dark:text-gray-500">[{entry_time}]</span>
      <span class="{color_class} text-sm font-mono">{msg}</span>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="cs">
{head("Tácek – Logy", CHIP_CSS)}
<body class="bg-gray-50 dark:bg-gray-900 min-h-screen">

  <header class="bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700">
    <div class="max-w-4xl mx-auto px-4 py-5 flex items-center justify-between">
      <div>
        <div class="flex items-baseline gap-2">
          <h1 class="text-2xl font-bold text-green-600 logo-glow">Tácek</h1>
          <span class="text-gray-400 dark:text-gray-500 text-sm font-medium">Logy</span>
        </div>
      </div>
      <a href="index.html" class="text-xs text-gray-400 dark:text-gray-500 hover:text-green-600 dark:hover:text-green-400">
        &larr; Zpět
      </a>
    </div>
  </header>

  <main class="max-w-4xl mx-auto px-4 py-8">
    <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
      <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-4">Běh scraper skriptu</h2>

      <div class="grid grid-cols-2 gap-4 mb-6 text-sm">
        <div>
          <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Začátek</p>
          <p class="text-gray-900 dark:text-gray-100 font-mono">{start_dt}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Konec</p>
          <p class="text-gray-900 dark:text-gray-100 font-mono">{end_dt}</p>
        </div>
      </div>

      <div class="border-t border-gray-200 dark:border-gray-700 pt-4">
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">Výstup ({len(logs)} záznamů)</p>
        <div class="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 font-mono text-xs overflow-x-auto">
          {logs_html}
        </div>
      </div>
    </div>
  </main>

  <footer class="text-center text-gray-300 dark:text-gray-600 text-xs py-8">
    Tácek – Logy běhu
  </footer>

  <script>
    {THEME_JS}
  </script>
</body>
</html>"""
