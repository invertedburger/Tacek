from tacek.config import PDF_LINKS, WEBPAGE_LINKS, RESULTS_DIR
from tacek.processor import split_links, process_all_pdfs, process_all_webpages, create_index_html, create_logs_html
from tacek.logger import init_logger, get_logger, log

if __name__ == '__main__':
    init_logger(RESULTS_DIR)
    log("Starting Tácek menu scraper...")

    pdfs, webpages = split_links(PDF_LINKS, WEBPAGE_LINKS)
    log(f"Processing {len(pdfs)} PDFs and {len(webpages)} webpages")

    pdf_sources = process_all_pdfs(pdfs)
    web_sources = process_all_webpages(webpages)
    create_index_html(RESULTS_DIR, pdf_sources + web_sources)
    create_logs_html(RESULTS_DIR)

    logger = get_logger()
    if logger:
        logger.save()
    log("Scraping complete!")
