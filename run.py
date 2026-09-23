import sys
from datetime import datetime
from tacek.config import (PDF_LINKS, WEBPAGE_LINKS, RESULTS_DIR, GEMINI_MODEL,
                          GROQ_TEXT_MODEL, GROQ_VISION_MODEL)
from tacek.processor import split_links, process_all_pdfs, process_all_webpages, create_index_html, create_logs_html
from tacek.logger import init_logger, get_logger, log
from tacek.ranking import has_today_menu
from tacek.processor import _load_json
import os

if __name__ == '__main__':
    init_logger(RESULTS_DIR)
    log("Starting Tácek menu scraper...")
    # Models get retired without warning; naming them makes a 404 self-evident.
    log(f"Models — Groq text: {GROQ_TEXT_MODEL or 'off'}, "
        f"Groq vision: {GROQ_VISION_MODEL or 'off'}, Gemini: {GEMINI_MODEL}")

    pdfs, webpages = split_links(PDF_LINKS, WEBPAGE_LINKS)
    log(f"Processing {len(pdfs)} PDFs and {len(webpages)} webpages")

    # Anything unexpected still has to leave a site and a readable log behind:
    # a crash here once skipped index generation entirely and the deploy went
    # out with the previous day's page.
    all_sources = []
    crashed = None
    try:
        all_sources = process_all_pdfs(pdfs) + process_all_webpages(webpages)
    except Exception as e:
        crashed = e
        log(f"ERROR: processing crashed: {e!r}")
    try:
        create_index_html(RESULTS_DIR, all_sources)
    except Exception as e:
        crashed = crashed or e
        log(f"ERROR: index generation failed: {e!r}")

    log("Scraping complete!")

    # Health check: on weekdays, at least one restaurant must have today's menu.
    # Run this BEFORE saving logs so its WARNING/ERROR messages land in logs.html.
    exit_code = 1 if crashed else 0
    dow = datetime.now().weekday()  # 0=Mon … 4=Fri, 5=Sat, 6=Sun
    if dow < 5:
        failed = [s['name'] for s in all_sources if s.get('no_menu')]
        ok = []
        for s in all_sources:
            if s.get('no_menu') or not s.get('result_file'):
                continue
            data_path = os.path.join(RESULTS_DIR, s['result_file'].replace('_results.html', '_data.json'))
            try:
                if has_today_menu(_load_json(data_path)):
                    ok.append(s['name'])
            except Exception:
                pass

        # A per-run summary, so logs.html answers "what is broken today?" at a
        # glance instead of only by reading every line.
        stale = [s['name'] for s in all_sources
                 if not s.get('no_menu') and s['name'] not in ok]
        log(f"Summary: {len(ok)}/{len(all_sources)} with today's menu"
            + (f" — ok: {', '.join(ok)}" if ok else '')
            + (f" | stale: {', '.join(stale)}" if stale else '')
            + (f" | failed: {', '.join(failed)}" if failed else ''))
        if failed:
            log(f"WARNING: parsing failed for: {', '.join(failed)}")
        if not ok:
            log("ERROR: No restaurant has today's menu — scraping may be broken!")
            exit_code = 1

    logger = get_logger()
    if logger:
        logger.save()
    create_logs_html(RESULTS_DIR)

    if exit_code:
        sys.exit(exit_code)
