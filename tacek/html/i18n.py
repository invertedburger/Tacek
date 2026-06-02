"""Central translation store for the static site (client-side i18n).

The server renders Czech text as the default (so the no-JS / pre-JS view is
Czech); `LANG_JS` in assets.py swaps `[data-i18n]` elements to the selected
language at runtime. `cs(key)` is used inline in the templates so Czech strings
live in exactly one place.
"""
import json

# key -> {"cs": ..., "en": ...}
STRINGS = {
    # ── index page ────────────────────────────────────────────
    "tagline":            {"cs": "Obědy v okolí Holandské · FODMAP & výživa",
                           "en": "Lunches near Holandská · FODMAP & nutrition"},
    "fodmap.desc":        {"cs": "Hodnotí, jak je jídlo vhodné pro citlivý žaludek. Nízký FODMAP = lepší volba.",
                           "en": "Rates how suitable a dish is for a sensitive stomach. Low FODMAP = better choice."},
    "fodmap.good":        {"cs": "Nízký = vhodné", "en": "Low = suitable"},
    "fodmap.bad":         {"cs": "Vysoký = riziko", "en": "High = risk"},
    "fitness.desc":       {"cs": "Celková výživová hodnota jídla – obsah bílkovin, kalorií a složení makronutrientů.",
                           "en": "Overall nutritional value of the dish – protein, calories and macronutrient composition."},
    "fitness.good":       {"cs": "Výborné = zdravé", "en": "Excellent = healthy"},
    "fitness.bad":        {"cs": "Slabé = méně vhodné", "en": "Poor = less suitable"},
    "restaurants":        {"cs": "Restaurace", "en": "Restaurants"},
    "weekend.line1":      {"cs": "Víkend — restaurace mají zavřeno.", "en": "Weekend — restaurants are closed."},
    "weekend.line2":      {"cs": "Menu se obnoví v pondělí v 10:37.", "en": "Menus refresh on Monday at 10:37."},
    "card.no_menu":       {"cs": "Menu dnes není k dispozici", "en": "Today's menu is not available"},
    "card.unavailable":   {"cs": "Menu nedostupné", "en": "Menu unavailable"},
    "card.original":      {"cs": "originál", "en": "original"},
    "card.recommend":     {"cs": "Doporučujeme dnes", "en": "Recommended today"},
    "card.updated":       {"cs": "Aktualizováno:", "en": "Updated:"},
    "card.view_menu":     {"cs": "Zobrazit celé menu", "en": "View full menu"},
    "card.stale_menu":    {"cs": "Menu z minulého dne", "en": "Previous day's menu"},
    "footer.index":       {"cs": "Tácek & Google Gemini", "en": "Tácek & Google Gemini"},

    # ── menu page ─────────────────────────────────────────────
    "menu.heading":       {"cs": "Analyzované menu", "en": "Analyzed menu"},
    "menu.subheading":    {"cs": "Analýza AI · Google Gemini", "en": "AI analysis · Google Gemini"},
    "menu.showing_today": {"cs": "Zobrazeno: dnes", "en": "Showing: today"},
    "week.show":          {"cs": "Zobrazit celý týden", "en": "Show whole week"},
    "week.today":         {"cs": "Jen dnes", "en": "Today only"},
    "menu.none_today":    {"cs": "Dnes žádné menu — zkuste ", "en": "No menu today — try "},
    "menu.none_today_link": {"cs": "zobrazit celý týden", "en": "showing the whole week"},
    "nutrition.protein":  {"cs": "bílkovin", "en": "protein"},
    "nutrition.carbs":    {"cs": "S", "en": "C"},
    "nutrition.fat":      {"cs": "T", "en": "F"},

    # ── filter / level words ──────────────────────────────────
    "filter.all":         {"cs": "Vše", "en": "All"},
    "fodmap.Low":         {"cs": "Nízký", "en": "Low"},
    "fodmap.Moderate":    {"cs": "Střední", "en": "Moderate"},
    "fodmap.High":        {"cs": "Vysoký", "en": "High"},
    "fitness.Low":        {"cs": "Slabé", "en": "Poor"},
    "fitness.Medium":     {"cs": "Dobré", "en": "Good"},
    "fitness.High":       {"cs": "Výborné", "en": "Excellent"},

    # ── shared header / tooltips ──────────────────────────────
    "nav.back":           {"cs": "Zpět", "en": "Back"},
    "nav.original":       {"cs": "Originál", "en": "Original"},
    "tip.logs":           {"cs": "Logy", "en": "Logs"},
    "tip.settings":       {"cs": "Nastavení", "en": "Settings"},
    "tip.theme":          {"cs": "Přepnout motiv", "en": "Toggle theme"},
    "tip.lang":           {"cs": "Change language", "en": "Změnit jazyk"},

    # ── profile page ──────────────────────────────────────────
    "profile.heading":    {"cs": "Dietní preference", "en": "Dietary preferences"},
    "profile.sub":        {"cs": "Uloženo lokálně · Automaticky aplikováno na stránkách menu",
                           "en": "Saved locally · Automatically applied on menu pages"},
    "profile.fodmap":     {"cs": "FODMAP filtr", "en": "FODMAP filter"},
    "profile.fodmap_sub": {"cs": "Výchozí filtr při otevření menu", "en": "Default filter when opening a menu"},
    "profile.fitness":    {"cs": "Fitness úroveň", "en": "Fitness level"},
    "profile.fitness_sub": {"cs": "Zobrazit pouze pokrmy s tímto fitness hodnocením",
                            "en": "Show only dishes with this fitness rating"},
    "profile.saved":      {"cs": "✓ Preference uloženy", "en": "✓ Preferences saved"},
    "profile.title":      {"cs": "Nastavení", "en": "Settings"},

    # ── logs page ─────────────────────────────────────────────
    "logs.label":         {"cs": "Logy", "en": "Logs"},
    "logs.none":          {"cs": "Žádné logy k dispozici", "en": "No logs available"},
    "logs.run":           {"cs": "Běh scraper skriptu", "en": "Scraper run"},
    "logs.start":         {"cs": "Začátek", "en": "Start"},
    "logs.end":           {"cs": "Konec", "en": "End"},
    "logs.output":        {"cs": "Výstup", "en": "Output"},
    "logs.entries":       {"cs": "záznamů", "en": "entries"},
    "logs.footer":        {"cs": "Tácek – Logy běhu", "en": "Tácek – Run logs"},

    # ── page titles (set via document.title) ──────────────────
    "title.index":        {"cs": "Tácek – Restaurace", "en": "Tácek – Restaurants"},
    "title.profile":      {"cs": "Nastavení – Tácek", "en": "Settings – Tácek"},
    "title.logs":         {"cs": "Tácek – Logy", "en": "Tácek – Logs"},
}

# Czech weekday name -> English (used by client-side day-label translation)
WEEKDAYS = {
    "Pondělí":  "Monday",
    "Úterý":    "Tuesday",
    "Středa":   "Wednesday",
    "Čtvrtek":  "Thursday",
    "Pátek":    "Friday",
    "Sobota":   "Saturday",
    "Neděle":   "Sunday",
}


def cs(key):
    """Czech default string for inline use in templates."""
    return STRINGS[key]["cs"]


CLIENT_JSON = json.dumps(STRINGS, ensure_ascii=False)
WEEKDAYS_JSON = json.dumps(WEEKDAYS, ensure_ascii=False)
