from tacek.config import PDF_LINKS, WEBPAGE_LINKS, RESULTS_DIR
from tacek.processor import split_links, process_all_pdfs, process_all_webpages, create_index_html

if __name__ == '__main__':
    pdfs, webpages = split_links(PDF_LINKS, WEBPAGE_LINKS)
    pdf_sources = process_all_pdfs(pdfs)
    web_sources = process_all_webpages(webpages)
    create_index_html(RESULTS_DIR, pdf_sources + web_sources)
