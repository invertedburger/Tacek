from tacek.html import i18n

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
    const today = new Date().toLocaleDateString('sv');
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
      document.querySelectorAll('[data-date]').forEach(sec => {
        const d = sec.dataset.date;
        // Undated sections (daily image menus with no date/weekday, e.g. U Tesaře)
        // are this-day-only by nature, so always show them under the today filter.
        const show = !todayOnly || !d || d === today;
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
      document.getElementById('todayBtn').textContent = todayOnly ? t('week.show') : t('week.today');
      applyFilters();
    }

    window._onLangChange = function() {
      const b = document.getElementById('todayBtn');
      if (b) b.textContent = todayOnly ? t('week.show') : t('week.today');
    };

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


# Client-side i18n. Embeds the translation tables, then swaps every [data-i18n]
# element on load and on toggle — same pattern as the dark-mode toggle.
LANG_JS = (
    "\n    const I18N = " + i18n.CLIENT_JSON + ";"
    "\n    const WEEKDAYS = " + i18n.WEEKDAYS_JSON + ";"
    + """
    function _curLang() { return document.documentElement.lang === 'en' ? 'en' : 'cs'; }
    function t(key) { const e = I18N[key]; return (e && e[_curLang()]) || (e && e.cs) || key; }

    function _detectLang() {
      const s = localStorage.getItem('lang');
      if (s === 'cs' || s === 'en') return s;
      return (navigator.language || '').toLowerCase().indexOf('en') === 0 ? 'en' : 'cs';
    }

    function _translateWeekdays(lang) {
      document.querySelectorAll('[data-weekday]').forEach(el => {
        let orig = el.getAttribute('data-weekday-orig');
        if (orig === null) { orig = el.textContent; el.setAttribute('data-weekday-orig', orig); }
        if (lang === 'en') {
          let out = orig;
          for (const cz in WEEKDAYS) out = out.replace(new RegExp(cz, 'gi'), WEEKDAYS[cz]);
          el.textContent = out;
        } else {
          el.textContent = orig;
        }
      });
    }

    function applyLang(lang) {
      document.documentElement.lang = lang;
      document.querySelectorAll('[data-i18n]').forEach(el => {
        const e = I18N[el.dataset.i18n];
        if (e && e[lang] != null) el.textContent = e[lang];
      });
      document.querySelectorAll('[data-i18n-attr]').forEach(el => {
        el.dataset.i18nAttr.split(',').forEach(pair => {
          const [attr, key] = pair.split(':').map(s => s.trim());
          const e = I18N[key];
          if (e && e[lang] != null) el.setAttribute(attr, e[lang]);
        });
      });
      _translateWeekdays(lang);
      if (window.PAGE_TITLE_KEY && I18N[window.PAGE_TITLE_KEY]) document.title = I18N[window.PAGE_TITLE_KEY][lang];
      if (window._onLangChange) window._onLangChange(lang);
      const lb = document.getElementById('langBtn');
      if (lb) lb.textContent = lang === 'cs' ? '🇬🇧' : '🇨🇿';
      localStorage.setItem('lang', lang);
    }

    (function() {
      const lb = document.getElementById('langBtn');
      if (lb) lb.addEventListener('click', () => applyLang(_curLang() === 'cs' ? 'en' : 'cs'));
      applyLang(_detectLang());
    })();"""
)


# ── Easter eggs ──────────────────────────────────────────────
# Hidden extras for whoever pokes at the page. Deliberately inert on a normal
# visit: every one is opt-in (a click streak, a key sequence, leaving the tab),
# nothing shifts layout, and the moving parts bow out under reduced motion.

EASTER_CSS = """<style>
    #egg-toast {
      position: fixed; left: 50%; bottom: 1.5rem; z-index: 9999;
      transform: translateX(-50%) translateY(1rem); opacity: 0;
      background: #111827; color: #f9fafb; box-shadow: 0 8px 24px rgba(0,0,0,.25);
      padding: 0.6rem 1rem; border-radius: 9999px; max-width: 90vw; text-align: center;
      font-size: 0.8125rem; font-weight: 500; pointer-events: none;
      transition: opacity .25s ease, transform .25s ease;
    }
    #egg-toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
    .dark #egg-toast { background: #f9fafb; color: #111827; }
    .egg-drop {
      position: fixed; top: -2rem; z-index: 9998; font-size: 1.5rem;
      pointer-events: none; animation: eggFall linear forwards;
    }
    @keyframes eggFall { to { transform: translateY(105vh) rotate(var(--spin, 360deg)); } }
    .egg-wobble { animation: eggWobble .4s ease; }
    @keyframes eggWobble {
      25% { transform: rotate(-7deg) scale(1.06); }
      75% { transform: rotate(7deg) scale(1.06); }
    }
    @media (prefers-reduced-motion: reduce) {
      .egg-drop   { display: none; }
      .egg-wobble { animation: none; }
      #egg-toast  { transition: none; }
    }
  </style>"""

EASTER_JS = """
    (function() {
      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      function toast(msg, ms) {
        let el = document.getElementById('egg-toast');
        if (!el) {
          el = document.createElement('div');
          el.id = 'egg-toast';
          document.body.appendChild(el);
        }
        el.textContent = msg;
        requestAnimationFrame(() => el.classList.add('show'));
        clearTimeout(el._t);
        el._t = setTimeout(() => el.classList.remove('show'), ms || 2600);
      }

      function rain(chars, n) {
        if (reduce) return;
        for (let i = 0; i < n; i++) {
          const d = document.createElement('div');
          d.className = 'egg-drop';
          d.textContent = chars[Math.floor(Math.random() * chars.length)];
          d.style.left = (Math.random() * 96) + 'vw';
          d.style.setProperty('--spin', (Math.random() * 720 - 360) + 'deg');
          d.style.animationDuration = (2 + Math.random() * 1.8) + 's';
          d.style.animationDelay = (Math.random() * 0.6) + 's';
          d.addEventListener('animationend', () => d.remove(), { once: true });
          document.body.appendChild(d);
        }
      }

      // 1. Tip the tray over — seven quick clicks on the logo and lunch spills.
      const logo = document.querySelector('.logo-glow');
      if (logo) {
        let hits = 0, last = 0;
        logo.addEventListener('click', () => {
          const now = Date.now();
          hits = (now - last < 1200) ? hits + 1 : 1;
          last = now;
          if (!reduce) {
            logo.classList.remove('egg-wobble');
            void logo.offsetWidth;
            logo.classList.add('egg-wobble');
          }
          if (hits >= 7) {
            hits = 0;
            rain(['🍲', '🍕', '🍗', '🥟', '🍺', '🥨', '🍰', '🥔'], 28);
            toast('Tácek se ti vysypal. Dobrou chuť!');
          }
        });
      }

      // 2. Konami code — for a few seconds nobody on the podium is a loser.
      const KONAMI = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
                      'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
      let pos = 0;
      document.addEventListener('keydown', e => {
        const k = e.key || '', want = KONAMI[pos];
        pos = (k === want || k.toLowerCase() === want) ? pos + 1 : 0;
        if (pos !== KONAMI.length) return;
        pos = 0;
        const medals = [].slice.call(document.querySelectorAll('.rec-day span.w-5'));
        const was = medals.map(m => m.textContent);
        medals.forEach(m => { if (m.textContent.trim()) m.textContent = '🏆'; });
        toast('🎮 Cheat aktivován: dneska se kalorie nepočítají.', 3400);
        setTimeout(() => medals.forEach((m, i) => { m.textContent = was[i]; }), 3400);
      });

      // 3. Leave the tab and it nags. The title is re-read on every hide, so the
      //    language toggle stays the authority on what the real one is.
      let realTitle = null;
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          realTitle = document.title;
          document.title = 'Vrať se, vychládá ti to 🍲';
        } else if (realTitle !== null) {
          document.title = realTitle;
          realTitle = null;
        }
      });

      // 4. For whoever opens DevTools on a lunch menu.
      console.log('%c🍽 Tácek', 'font-size:20px;font-weight:bold;color:#22c55e');
      console.log('%cHledáš oběd i v konzoli? Respekt. Zkus ↑↑↓↓←→←→BA.', 'color:#6b7280');
    })();"""
