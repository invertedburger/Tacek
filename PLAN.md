# Tácek — Plan & Operational Runbook

Living document for architecture decisions, deployment topology, and how to
operate the daily pipeline. For code structure and conventions see
[CLAUDE.md](CLAUDE.md); for user-facing setup see [README.md](README.md).

## Goal

Every weekday before lunch, publish a static site ranking nearby restaurants'
lunch dishes by FODMAP and fitness, so the choice of where to eat takes seconds.
Freshness matters: today's menu must be live by the time people decide on lunch
(~11:00–12:00 Prague).

## Deployment topology

```text
Oracle Free Tier VM (Ubuntu, 130.162.224.103)
  └─ cron (Europe/Prague, Mon–Fri 10:37 & 11:37)
       └─ deploy/trigger_github.sh
            └─ GitHub API workflow_dispatch  (PAT in ~/.github_pat, scope: workflow)
                 └─ .github/workflows/build.yml
                      ├─ run.py  → results/  (HTML + JSON)
                      ├─ deploy to GitHub Pages  → jidlo.ivomartisek.cz
                      └─ FTP upload (optional; skipped when ftp_host empty)
```

Why an external trigger instead of GitHub's `schedule:`? GitHub-hosted cron is
frequently delayed 10–30 minutes under load, which is unacceptable when the menu
must be fresh by lunchtime. The Oracle VM fires `workflow_dispatch` on a precise
schedule. The build itself still also runs on every push to `main`.

## Pipeline (run.py)

1. `split_links` — `pdf_links` are treated as PDF sources, `webpage_links` routed
   by `.pdf` suffix.
2. `process_all_pdfs` — for each PDF source: `resolve_pdf_link` (scrape page for
   the current PDF if the entry isn't a direct `.pdf`) → download → hash → cache
   check → `analyze_pdf` → menu HTML.
3. `process_all_webpages` — download → extract text/images → cache check →
   Groq (primary) / Gemini (fallback) → menu HTML.
4. `create_index_html` — geocode, compute top dishes + recommendation date per
   restaurant, render `index.html` + `profile.html`.
5. Health check — on weekdays, exit non-zero if no restaurant has today's menu.

## Key design decisions

- **Dynamic PDF resolution.** Restaurants (Eatology / IQ Brno) publish menus at
  weekly-changing hashed storage URLs. `pdf_links` therefore points at the
  restaurant *page*; `downloader.resolve_pdf_link` extracts the live PDF link at
  run time. Identity stays keyed on the page domain so caches/markers are stable.
  The PDF cache key is the stable `source_name` (not the weekly-changing
  filename), with freshness decided by the file content hash.
- **Weekday-aware "today".** Image/undated menus label days only by name
  (Pondělí…). `ranking._weekday_date` resolves a weekday name to its date in the
  current week, so a weekly menu shows only today's dishes instead of pooling the
  whole week as today. Truly label-less days still fall back to "treat as today".
- **Caching by content hash.** PDFs by file hash, text pages by extracted-text
  hash, image pages by image-bytes hash. A menu change invalidates automatically.
- **No build step on the client.** All HTML is generated as f-strings; all
  interactivity is inline JS. i18n strings live once in `tacek/html/i18n.py`.
- **Pre-trigger UX.** Before the daily build runs, Pages still serves yesterday's
  output. The index shows a "menu is being prepared" banner (until ~noon, when no
  card has today's data) so the site reads as *pending*, not *dead*.

## Operational runbook

### Daily trigger is failing

```bash
ssh ubuntu@130.162.224.103
tail -20 ~/tacek/trigger.log         # look for "dispatch HTTP <code>"
~/tacek/deploy/trigger_github.sh     # run manually; expect HTTP 204
```

- **HTTP 401** → PAT expired or revoked (fine-grained tokens expire). Mint a new
  token with the `workflow` scope and the repo's Actions read/write, then:
  `echo "<TOKEN>" > ~/.github_pat && chmod 600 ~/.github_pat`.
- **HTTP 404** → wrong repo/workflow/branch in `trigger_github.sh`.
- **Nothing in trigger.log at 10:37** → cron not firing. Check
  `systemctl is-active cron`, `crontab -l` (must show `CRON_TZ=Europe/Prague` and
  `/home/ubuntu/...` paths), and `grep CRON /var/log/syslog`.

### A restaurant shows no / wrong menu

- Inspect `results/<domain>_data.json` and the run log (`logs.html`).
- Force re-analysis: delete the restaurant's line from
  `results/processed_files.log` or `results/processed_webpages.log`.
- For dynamic-PDF sites, confirm `resolve_pdf_link` still finds a `.pdf` on the
  page (the markup may have changed).

## Restaurants

| Restaurant | Domain | Source |
| --- | --- | --- |
| Eatology (IQ Brno) | `www.iqrestaurant.cz` | page → dynamic PDF |
| Il Paladar | `www.ilpaladar.cz` | webpage (text) |
| U Tesaře | `www.utesare.cz` | image (weekday-named) |
| U Hovězího Pupku | `www.uhovezihopupku.cz` | webpage (text) |
| Kometa Pub | `www.kometapub.cz` | webpage (text) |
| Buddha 2 | `www.menicka.cz` | webpage (menicka iframe) |

## Backlog / ideas

- Detect cross-week staleness for undated image menus (can't be done from a
  weekday name alone; would need the restaurant to date the image or an OCR date).
- Consider a lightweight status endpoint so the pre-trigger banner reflects real
  build state instead of a client-side time heuristic.
- Rotate the GitHub PAT automatically / alert before expiry.
