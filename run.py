import sys
from datetime import datetime
from tacek.config import PDF_LINKS, WEBPAGE_LINKS, RESULTS_DIR
from tacek.processor import split_links, process_all_pdfs, process_all_webpages, create_index_html, create_logs_html
from tacek.logger import init_logger, get_logger, log
from tacek.ranking import has_today_menu
from tacek.processor import _load_json
import os

if __name__ == '__main__':
    init_logger(RESULTS_DIR)
    log("Starting Tácek menu scraper...")

    pdfs, webpages = split_links(PDF_LINKS, WEBPAGE_LINKS)
    log(f"Processing {len(pdfs)} PDFs and {len(webpages)} webpages")

    pdf_sources = process_all_pdfs(pdfs)
    web_sources = process_all_webpages(webpages)
    all_sources = pdf_sources + web_sources
    create_index_html(RESULTS_DIR, all_sources)

    logger = get_logger()
    if logger:
        log("Scraping complete!")
        logger.save()
    create_logs_html(RESULTS_DIR)

    # Health check: on weekdays, at least one restaurant must have today's menu
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

        if failed:
            log(f"WARNING: parsing failed for: {', '.join(failed)}")
        if not ok:
            log("ERROR: No restaurant has today's menu — scraping may be broken!")
            sys.exit(1)
