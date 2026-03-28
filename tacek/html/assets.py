DARK_INIT = "<script>if(localStorage.getItem('theme')==='dark')document.documentElement.classList.add('dark');</script>"

TAILWIND = "<script src=\"https://cdn.tailwindcss.com\"></script>\n  <script>tailwind.config={darkMode:'class'}</script>"

CHIP_CSS = """<style>
    .chip-active   { background: #22c55e; color: white; border-color: #22c55e; }
    .chip-inactive { background: transparent; border-color: #e5e7eb; color: #6b7280; cursor: pointer; transition: all 0.15s; }
    .dark .chip-inactive { border-color: #4b5563; color: #9ca3af; }
    .chip-inactive:hover { background: #f9fafb; }
    .dark .chip-inactive:hover { background: #374151; }
    .chip-inactive:active, .chip-active:active { transform: scale(0.93); }
    [data-color="green"].chip-inactive { color: #15803d; border-color: #86efac; }
    [data-color="amber"].chip-inactive { color: #b45309; border-color: #fcd34d; }
    [data-color="red"].chip-inactive   { color: #b91c1c; border-color: #fca5a5; }
    .dark [data-color="green"].chip-inactive { color: #4ade80; border-color: #166534; }
    .dark [data-color="amber"].chip-inactive { color: #fbbf24; border-color: #78350f; }
    .dark [data-color="red"].chip-inactive   { color: #f87171; border-color: #7f1d1d; }
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(16px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .anim-card { animation: fadeUp 0.4s ease both; }
    [data-fodmap] { transition: opacity 0.18s ease, transform 0.18s ease, max-height 0.25s ease; overflow: hidden; }
    [data-fodmap].filtering-out { opacity: 0; transform: scale(0.97); }
    .card-hover { transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease, background-color 0.2s ease; }
    .card-hover:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.10); }
    .dark .card-hover:hover { border-color: #374151; background-color: #252f3e; box-shadow: 0 4px 16px rgba(0,0,0,0.5); }
    @keyframes logoPulse {
      0%, 100% { text-shadow: 0 0 6px rgba(34,197,94,0); }
      50%       { text-shadow: 0 0 14px rgba(34,197,94,0.55); }
    }
    .logo-glow { animation: logoPulse 3s ease-in-out infinite; }
  </style>"""

THEME_JS = """
    const themeBtn = document.getElementById('themeBtn');
    function _updateThemeBtn() {
      themeBtn.textContent = document.documentElement.classList.contains('dark') ? '\u2600' : '\u263e';
    }
    themeBtn.addEventListener('click', () => {
      const isDark = document.documentElement.classList.contains('dark');
      localStorage.setItem('theme', isDark ? 'light' : 'dark');
      document.documentElement.classList.toggle('dark', !isDark);
      _updateThemeBtn();
    });
    _updateThemeBtn();"""

FILTER_JS = """
    let fodmapFilter  = localStorage.getItem('fodmapFilter')  || 'all';
    let fitnessFilter = localStorage.getItem('fitnessFilter') || 'all';
    let todayOnly = true;
    const today = new Date().toISOString().slice(0, 10);
    const _FODMAP_RANK  = { Low: 0, Moderate: 1, High: 2 };
    const _FITNESS_RANK = { High: 0, Medium: 1, Low: 2 };

    function applyFilters() {
      document.querySelectorAll('[data-fodmap]').forEach(el => {
        const showF   = fodmapFilter  === 'all' || _FODMAP_RANK[el.dataset.fodmap]  <= _FODMAP_RANK[fodmapFilter];
        const showFit = fitnessFilter === 'all' || _FITNESS_RANK[el.dataset.fitness] <= _FITNESS_RANK[fitnessFilter];
        const visible = showF && showFit;
        if (!visible && el.style.display !== 'none') {
          el.classList.add('filtering-out');
          setTimeout(() => { el.style.display = 'none'; el.classList.remove('filtering-out'); }, 180);
        } else if (visible) {
          el.style.display = '';
          requestAnimationFrame(() => el.classList.remove('filtering-out'));
        }
      });
      const todayDow = new Date().getDay();
      const isWeekend = todayDow === 0 || todayDow === 6;
      document.querySelectorAll('[data-date]').forEach(sec => {
        const d = sec.dataset.date;
        const show = !todayOnly || (d ? d === today : isWeekend);
        sec.style.display = show ? '' : 'none';
      });
      const noToday = document.getElementById('noToday');
      if (noToday) {
        const any = [...document.querySelectorAll('[data-date]')].some(s => s.style.display !== 'none');
        noToday.style.display = (todayOnly && !any) ? '' : 'none';
      }
      _refreshFilterChips();
    }

    function setFodmapFilter(v)  { fodmapFilter  = v; applyFilters(); }
    function setFitnessFilter(v) { fitnessFilter = v; applyFilters(); }

    function toggleToday() {
      todayOnly = !todayOnly;
      document.getElementById('todayBtn').textContent = todayOnly ? 'Zobrazit celý týden' : 'Jen dnes';
      applyFilters();
    }

    function _refreshFilterChips() {
      document.querySelectorAll('[data-filter]').forEach(btn => {
        const active = (btn.dataset.filter === 'fodmap'  && btn.dataset.value === fodmapFilter) ||
                       (btn.dataset.filter === 'fitness' && btn.dataset.value === fitnessFilter);
        btn.classList.toggle('chip-active',   active);
        btn.classList.toggle('chip-inactive', !active);
      });
    }

    applyFilters();
    document.querySelectorAll('.anim-card').forEach(el => {
      el.addEventListener('animationend', () => { el.style.animation = 'none'; }, { once: true });
    });"""

PROFILE_JS = """
    function setFodmapPref(value) {
      localStorage.setItem('fodmapFilter', value);
      _refreshProfileChips();
      _showSaved();
    }

    function setFitnessPref(value) {
      localStorage.setItem('fitnessFilter', value);
      _refreshProfileChips();
      _showSaved();
    }

    function _refreshProfileChips() {
      const f  = localStorage.getItem('fodmapFilter')  || 'all';
      const fi = localStorage.getItem('fitnessFilter') || 'all';
      document.querySelectorAll('[data-pref-filter]').forEach(btn => {
        const isActive = (btn.dataset.prefFilter === 'fodmap'  && btn.dataset.value === f) ||
                         (btn.dataset.prefFilter === 'fitness' && btn.dataset.value === fi);
        btn.classList.toggle('chip-active',   isActive);
        btn.classList.toggle('chip-inactive', !isActive);
      });
    }

    function _showSaved() {
      const el = document.getElementById('savedMsg');
      el.classList.remove('hidden');
      setTimeout(() => el.classList.add('hidden'), 2000);
    }

    _refreshProfileChips();"""
