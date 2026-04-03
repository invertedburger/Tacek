import re
import json
import os
import base64
import tempfile
from google import genai
from google.genai import types
from tacek.config import API_KEY, GEMINI_MODEL, GROQ_API_KEY
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

JSON_PROMPT = """Extract all foods from this menu. Return ONLY valid JSON with this exact structure, no markdown, no code fences, no extra text:
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
Rules:
- fodmap_level must be exactly one of: "Low", "Moderate", "High"
- fitness_level must be exactly one of: "Low", "Medium", "High"
- Always keep original Czech food names
- protein_g, carbs_g, fat_g, calories_kcal are estimated integers
- If the image/text does NOT contain an actual restaurant menu with specific dishes, return {"days": []}
- Do NOT invent or guess menu items — only extract what is explicitly listed"""

_GROQ_TEXT_MODEL = "llama-3.3-70b-versatile"
_GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def _parse(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    return json.loads(text.strip())


# ── Groq (primary) ─────────────────────────────────────────

def _groq_text(text, source_name):
    if not _groq:
        return None
    try:
        log(f"Analyzing {source_name} with Groq...")
        resp = _groq.chat.completions.create(
            model=_GROQ_TEXT_MODEL,
            messages=[{"role": "user", "content": JSON_PROMPT + f"\n\nMenu text from {source_name}:\n{text}"}],
            response_format={"type": "json_object"},
        )
        return _parse(resp.choices[0].message.content)
    except Exception as e:
        log(f"ERROR: Groq text failed for {source_name}: {e}")
        return None


def _groq_image(image_path):
    if not _groq:
        return None
    try:
        log(f"Analyzing image with Groq: {image_path}")
        img_bytes, mime = _downscale_image(image_path)
        b64 = base64.b64encode(img_bytes).decode()
        resp = _groq.chat.completions.create(
            model=_GROQ_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": JSON_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }],
            response_format={"type": "json_object"},
        )
        result = _parse(resp.choices[0].message.content)
        log(f"Groq vision extracted {len(result.get('days', []))} day(s) from {os.path.basename(image_path)}")
        return result
    except Exception as e:
        log(f"ERROR: Groq vision failed for {image_path}: {e}")
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
        resp = _gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=JSON_PROMPT + f"\n\nMenu text from {source_name}:\n{text}",
            config=_JSON_CONFIG,
        )
        return _parse(resp.text)
    except Exception as e:
        log(f"ERROR: Gemini text failed for {source_name}: {e}")
        return None


def _gemini_image(image_path):
    try:
        log(f"Trying Gemini fallback for image: {image_path}")
        uploaded = _gemini.files.upload(file=image_path)
        resp = _gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=[JSON_PROMPT, uploaded],
            config=_JSON_CONFIG,
        )
        return _parse(resp.text)
    except Exception as e:
        log(f"ERROR: Gemini image failed for {image_path}: {e}")
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
        uploaded = _gemini.files.upload(file=normalized)
        resp = _gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=[JSON_PROMPT, uploaded],
            config=_JSON_CONFIG,
        )
        return _parse(resp.text)
    except Exception as e:
        log(f"WARNING: Gemini PDF API failed for {pdf_path}: {e}")

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
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img_page = new_doc.new_page(width=pix.width, height=pix.height)
            img_page.insert_image(img_page.rect, pixmap=pix)
        new_doc.save(out)
        new_doc.close()
        doc.close()
        log(f"Image-based PDF re-save successful ({doc.page_count} pages)")
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
