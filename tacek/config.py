import os
import json

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load config.json with error handling
_cfg_path = os.path.join(_root, 'config.json')
try:
    with open(_cfg_path, 'r', encoding='utf-8') as _f:
        _cfg = json.load(_f)
except FileNotFoundError:
    raise FileNotFoundError(f"config.json not found at {_cfg_path}") from None
except json.JSONDecodeError as e:
    raise ValueError(f"config.json is invalid JSON: {e}") from e

# Load secrets.json with error handling
_sec_path = os.path.join(_root, 'secrets.json')
try:
    with open(_sec_path, 'r', encoding='utf-8') as _f:
        _sec = json.load(_f)
except FileNotFoundError:
    raise FileNotFoundError(f"secrets.json not found at {_sec_path}") from None
except json.JSONDecodeError as e:
    raise ValueError(f"secrets.json is invalid JSON: {e}") from e

# Validate required keys in config
_required_cfg_keys = ['pdf_links', 'webpage_links', 'restaurant_names']
for _key in _required_cfg_keys:
    if _key not in _cfg:
        raise KeyError(f"Missing required key in config.json: {_key}")

# Validate required keys in secrets
_required_sec_keys = ['gemini_api_key', 'ftp_host', 'ftp_user', 'ftp_pass']
for _key in _required_sec_keys:
    if _key not in _sec:
        raise KeyError(f"Missing required key in secrets.json: {_key}")

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
# Groq retires models without notice; keep the ids in config.json so a
# decommission is a config edit. Empty vision model = skip Groq for images.
GROQ_TEXT_MODEL            = _cfg.get('groq_text_model', 'openai/gpt-oss-120b')
GROQ_VISION_MODEL          = _cfg.get('groq_vision_model', '')
# Reasoning models spend the completion budget on thinking and then return
# an empty body, which Groq rejects as invalid JSON — hence both knobs.
GROQ_REASONING_EFFORT      = _cfg.get('groq_reasoning_effort', 'low')
GROQ_MAX_TOKENS            = _cfg.get('groq_max_tokens', 8000)

API_KEY      = _sec['gemini_api_key']
GROQ_API_KEY = _sec.get('groq_api_key', '')
FTP_HOST = _sec['ftp_host']
FTP_USER = _sec['ftp_user']
FTP_PASS = _sec['ftp_pass']
FTP_DIR  = _sec.get('ftp_dir', '')
