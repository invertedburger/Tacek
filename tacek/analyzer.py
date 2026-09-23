import re
import json
import os
import time
import base64
import tempfile
from google import genai
from google.genai import types
from tacek.config import (API_KEY, GEMINI_MODEL, GROQ_API_KEY, GROQ_TEXT_MODEL,
                          GROQ_VISION_MODEL, GROQ_REASONING_EFFORT, GROQ_MAX_TOKENS)
from tacek.logger import log

_gemini = genai.Client(api_key=API_KEY)
_JSON_CONFIG = types.GenerateContentConfig(response_mime_type="application/json")

_groq = None
if GROQ_API_KEY:
    try:
        from openai import OpenAI
        _groq = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
    except ImportError:
        log("WARNING: openai package not installed, Groq disabled.")

JSON_PROMPT = """You are a nutrition analyst for a Czech lunch-menu site. Extract every dish from this menu and rate it carefully. Return ONLY valid JSON with this exact structure, no markdown, no code fences, no extra text:
{
  "days": [
    {
      "day": "Day label e.g. Monday 17.3.2026",
      "dishes": [
        {
          "name": "original Czech food name",
          "fitness_level": "High",
          "fodmap_level": "Low",
          "problematic_ingredients": ["gluten", "onion"],
          "protein_g": 35,
          "carbs_g": 45,
          "fat_g": 15,
          "calories_kcal": 450
        }
      ]
    }
  ]
}

== fodmap_level (gut tolerance — exactly "Low", "Moderate", or "High") ==
Judge by FODMAP-triggering ingredients, INCLUDING ones hidden in sauces and stocks.
- HIGH-FODMAP triggers: onion, garlic (extremely common in Czech sauces/guláš/svíčková — assume present unless clearly absent), wheat/gluten (knedlíky, rohlík, breading/"smažený", pasta, roux/"jíška"), legumes (čočka, fazole, cizrna, hrách), large amounts of milk/cream ("smetana", creamy sauces), honey/"med", apple/pear, mango, cauliflower, mushrooms in quantity, cabbage/"zelí" in quantity.
- "Low"  = no significant triggers: plain grilled/roasted meat or fish, rice, potatoes, carrot, courgette, lettuce, eggs, hard cheese, citrus.
- "High" = a primary component is a strong trigger (onion/garlic-heavy sauce, breaded/floured dish, knedlíky, legume base, heavy cream sauce).
- "Moderate" = triggers present but secondary or in small amounts.
List the actual triggers you found in problematic_ingredients (e.g. ["onion","garlic","gluten","lactose"]); use [] if none.

== fitness_level (overall nutritional quality — exactly "Low", "Medium", or "High") ==
Reward protein and vegetables; penalise deep-frying, heavy cream, and refined-carb-heavy / low-protein plates.
- "High"   = lean protein-forward, grilled/baked/steamed/sous-vide, with vegetables or a sensible side (e.g. grilled chicken breast + rice + salad, baked fish, steak + vegetables). Roughly protein >= 30 g and not deep-fried.
- "Medium" = balanced but heavier — roasted meat with knedlíky/potatoes, moderate sauce, decent protein with more refined carbs or fat.
- "Low"    = deep-fried/breaded ("smažený", "řízek", hranolky), heavy cream/roux sauces, sweet mains ("buchtičky", "lívance", sladké), or mostly refined carbs with little protein.

== macros (estimated integers for ONE typical restaurant lunch portion) ==
- Assume a standard Czech lunch portion (main ~120-200 g protein source plus its stated side).
- Base the estimate on the actual components named; be realistic, not optimistic.
- Keep them internally consistent: calories_kcal should ≈ protein_g*4 + carbs_g*4 + fat_g*9 (within ~10%).

== day labels (critical for showing the correct day) ==
- Create one entry in days[] per distinct day the menu shows. A weekly menu yields one entry per weekday; a single-day menu yields one entry.
- Set "day" to that day's date and/or weekday name EXACTLY as printed on the menu, e.g. "Pondělí 9.6.2026", "Úterý 10.6.", or just "Středa". Copy whatever date or weekday is shown verbatim.
- NEVER leave "day" empty or blank when any date or weekday name is visible anywhere on the menu (header, corner, per-day heading) — always copy it. Use an empty label ONLY when the menu shows no date and no weekday at all.
- If the menu states a date RANGE for the whole week (e.g. "14. 9. - 18. 9. 2026"), never copy the range itself into "day". Count the days forward from the start of the range so that EVERY label ends with its own date: "Pondělí 14.9.2026", "Úterý 15.9.2026", "Středa 16.9.2026" and so on. A bare weekday name is wrong whenever the menu shows a range — the week it belongs to would be lost.
- NEVER invent a date or weekday that is not printed on the menu. A menu headed only "Víkendová nabídka" or "Polední nabídka" with no date gets an empty "day" — guessing a weekday makes the site show the wrong day's food.

== general rules ==
- Always keep the original Czech food name verbatim.
- Do NOT invent or guess dishes — extract only what is explicitly listed.
- Soups/"polévka" and the daily soup line still get extracted if listed.
- If the image/text is NOT an actual menu with specific dishes, return {"days": []}."""

_GROQ_TEXT_MODEL = GROQ_TEXT_MODEL
_GROQ_VISION_MODEL = GROQ_VISION_MODEL


def _groq_kwargs():
    """Call options a reasoning model needs to actually emit the JSON body."""
    opts = {"response_format": {"type": "json_object"}, "max_completion_tokens": GROQ_MAX_TOKENS}
    if GROQ_REASONING_EFFORT:
        opts["reasoning_effort"] = GROQ_REASONING_EFFORT
    return opts


def _parse(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    # Models occasionally tack stray closing brackets onto otherwise valid JSON,
    # so decode the first complete value instead of failing on the leftovers.
    obj, _ = json.JSONDecoder().raw_decode(text.strip())
    return obj


def _short(e, limit=200):
    """One-line, trimmed error text — a raw provider error can run to kilobytes."""
    msg = ' '.join(str(e).split())
    return msg if len(msg) <= limit else msg[:limit] + '…'


_TRANSIENT = ('UNAVAILABLE', 'RESOURCE_EXHAUSTED', 'overloaded', 'rate_limit',
              '503', '502', '500', '429')


def _is_transient(e):
    msg = str(e)
    return any(marker in msg for marker in _TRANSIENT)


def _with_retry(call, what, attempts=3, base_delay=4):
    """Run call(), retrying provider hiccups — a 503 must not blank a menu."""
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except Exception as e:
            if attempt == attempts or not _is_transient(e):
                raise
            delay = base_delay * attempt
            log(f"{what} is busy ({_short(e, 80)}), retrying in {delay}s [{attempt}/{attempts - 1}]")
            time.sleep(delay)


def _failed_generation(e):
    """The text Groq generated but rejected, when its own JSON check trips."""
    body = getattr(e, 'body', None)
    if isinstance(body, dict):
        error = body.get('error')
        if isinstance(error, dict):
            return error.get('failed_generation')
    return None


def _salvage(e, source_name):
    """Recover a rejected-but-parseable Groq completion, or None."""
    gen = _failed_generation(e)
    if not gen:
        return None
    try:
        data = _parse(gen)
    except Exception:
        return None
    log(f"Recovered {source_name} from Groq's rejected output ({len(data.get('days', []))} day(s))")
    return data


# ── Groq (primary) ─────────────────────────────────────────

def _groq_text(text, source_name):
    if not _groq:
        return None
    try:
        log(f"Analyzing {source_name} with Groq...")
        resp = _with_retry(lambda: _groq.chat.completions.create(
            model=_GROQ_TEXT_MODEL,
            messages=[{"role": "user", "content": JSON_PROMPT + f"\n\nMenu text from {source_name}:\n{text}"}],
            **_groq_kwargs(),
        ), f"Groq ({source_name})")
        return _parse(resp.choices[0].message.content)
    except Exception as e:
        salvaged = _salvage(e, source_name)
        if salvaged is not None:
            return salvaged
        log(f"ERROR: Groq text failed for {source_name}: {_short(e)}")
        return None


def _groq_image(image_path):
    if not _groq or not _GROQ_VISION_MODEL:
        return None
    try:
        log(f"Analyzing image with Groq: {image_path}")
        img_bytes, mime = _downscale_image(image_path)
        b64 = base64.b64encode(img_bytes).decode()
        resp = _with_retry(lambda: _groq.chat.completions.create(
            model=_GROQ_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": JSON_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }],
            **_groq_kwargs(),
        ), "Groq vision")
        result = _parse(resp.choices[0].message.content)
        log(f"Groq vision extracted {len(result.get('days', []))} day(s) from {os.path.basename(image_path)}")
        return result
    except Exception as e:
        salvaged = _salvage(e, os.path.basename(image_path))
        if salvaged is not None:
            return salvaged
        log(f"ERROR: Groq vision failed for {image_path}: {_short(e)}")
        return None


def _downscale_image(image_path, max_width=1024):
    try:
        from PIL import Image
        import io
        img = Image.open(image_path)
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return buf.getvalue(), 'image/jpeg'
    except ImportError:
        with open(image_path, 'rb') as f:
            data = f.read()
        ext = os.path.splitext(image_path)[1].lower().lstrip('.')
        mime = f"image/{ext}" if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp') else "image/jpeg"
        return data, mime


# ── Gemini (backup) ─────────────────────────────────────────

def _gemini_text(text, source_name):
    try:
        log(f"Trying Gemini fallback for {source_name}...")
        resp = _with_retry(lambda: _gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=JSON_PROMPT + f"\n\nMenu text from {source_name}:\n{text}",
            config=_JSON_CONFIG,
        ), f"Gemini ({source_name})")
        return _parse(resp.text)
    except Exception as e:
        log(f"ERROR: Gemini text failed for {source_name}: {_short(e)}")
        return None


def _gemini_image(image_path):
    try:
        # Not a fallback when Groq has no vision model configured — say so,
        # so the run log does not read as if Groq had failed.
        why = "fallback" if _GROQ_VISION_MODEL else "analysis"
        log(f"Gemini image {why}: {os.path.basename(image_path)}")
        uploaded = _with_retry(lambda: _gemini.files.upload(file=image_path), "Gemini upload")
        resp = _with_retry(lambda: _gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=[JSON_PROMPT, uploaded],
            config=_JSON_CONFIG,
        ), "Gemini image")
        return _parse(resp.text)
    except Exception as e:
        log(f"ERROR: Gemini image failed for {os.path.basename(image_path)}: {_short(e)}")
        return None


# ── Public API ──────────────────────────────────────────────

def analyze_text(text, source_name):
    """Groq first, Gemini backup."""
    result = _groq_text(text, source_name)
    if result and result.get('days'):
        return result
    return _gemini_text(text, source_name)


def analyze_image(image_path):
    """Groq vision first, Gemini backup."""
    result = _groq_image(image_path)
    if result and result.get('days'):
        return result
    return _gemini_image(image_path)


def analyze_pdf(pdf_path):
    """Try Gemini file API first (best for PDFs), then image rendering, then text."""
    normalized = _resave_pdf(pdf_path)
    try:
        uploaded = _with_retry(lambda: _gemini.files.upload(file=normalized), "Gemini upload")
        resp = _with_retry(lambda: _gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=[JSON_PROMPT, uploaded],
            config=_JSON_CONFIG,
        ), "Gemini (PDF)")
        return _parse(resp.text)
    except Exception as e:
        log(f"WARNING: Gemini PDF API failed for {os.path.basename(pdf_path)}: {_short(e)}")
    finally:
        if normalized != pdf_path and os.path.exists(normalized):
            try:
                os.remove(normalized)
            except OSError:
                pass

    # Try image rendering (uses Groq vision → Gemini as fallback per page)
    log("Falling back to image rendering...")
    result = _analyze_pdf_as_images(pdf_path)
    if result:
        return result

    # Last resort: text extraction
    return _analyze_pdf_as_text(pdf_path)


def _resave_pdf(pdf_path):
    try:
        import fitz
        doc = fitz.open(pdf_path)
        out = pdf_path + '.normalized.pdf'
        log(f"PDF has {doc.page_count} pages, re-saving...")
        # Try simple re-save first
        try:
            doc.save(out)
            doc.close()
            log(f"PDF re-saved successfully to {out}")
            return out
        except Exception as e1:
            log(f"Simple re-save failed ({type(e1).__name__}: {e1}), trying image-based re-save...")
        # Fallback: create new PDF from rendered page images
        new_doc = fitz.open()
        page_count = doc.page_count
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img_page = new_doc.new_page(width=pix.width, height=pix.height)
            img_page.insert_image(img_page.rect, pixmap=pix)
        doc.close()
        new_doc.save(out)
        new_doc.close()
        log(f"Image-based PDF re-save successful ({page_count} pages)")
        return out
    except Exception as e:
        log(f"WARNING: PDF re-save completely failed ({type(e).__name__}: {e})")
        return pdf_path


def _analyze_pdf_as_images(pdf_path):
    try:
        import fitz
    except ImportError:
        log("ERROR: pymupdf not installed.")
        return None
    try:
        doc = fitz.open(pdf_path)
        merged = {'days': []}
        with tempfile.TemporaryDirectory() as tmp:
            for i, page in enumerate(doc):
                img_path = os.path.join(tmp, f"page_{i}.png")
                page.get_pixmap(dpi=150).save(img_path)
                data = analyze_image(img_path)
                if data:
                    merged['days'].extend(data.get('days', []))
        if merged['days']:
            return merged
        log("Image analysis returned no data, trying text extraction...")
        return None
    except Exception as e:
        log(f"ERROR rendering PDF images: {e}")
        return None


def _analyze_pdf_as_text(pdf_path):
    try:
        import fitz
        doc = fitz.open(pdf_path)
        text = '\n'.join(page.get_text() for page in doc).strip()
        if len(text) < 50:
            log("PDF text extraction yielded too little text.")
            return None
        log(f"Extracted {len(text)} chars from PDF, analyzing as text...")
        return analyze_text(text, os.path.basename(pdf_path))
    except Exception as e:
        log(f"ERROR extracting text from PDF: {e}")
        return None
