import os
import json

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(_root, 'config.json'), 'r', encoding='utf-8') as _f:
    _cfg = json.load(_f)

with open(os.path.join(_root, 'secrets.json'), 'r', encoding='utf-8') as _f:
    _sec = json.load(_f)

PDF_LINKS                  = _cfg['pdf_links']
WEBPAGE_LINKS              = _cfg['webpage_links']
RESTAURANT_NAMES           = _cfg['restaurant_names']
RESTAURANT_DISPLAY_NAMES   = _cfg.get('restaurant_display_names', {})
RESTAURANT_COORDS_OVERRIDE = _cfg.get('restaurant_coords_override', {})
WEBPAGE_PARSERS            = _cfg.get('webpage_parsers', {})
DOWNLOAD_DIR               = _cfg.get('download_dir', 'menus')
RESULTS_DIR                = _cfg.get('results_dir', 'results')
MIN_MENU_TEXT_LENGTH       = _cfg.get('min_menu_text_length', 200)
GEMINI_MODEL               = _cfg.get('gemini_model', 'models/gemini-2.5-flash')

API_KEY  = _sec['gemini_api_key']
FTP_HOST = _sec['ftp_host']
FTP_USER = _sec['ftp_user']
FTP_PASS = _sec['ftp_pass']
FTP_DIR  = _sec.get('ftp_dir', '')
