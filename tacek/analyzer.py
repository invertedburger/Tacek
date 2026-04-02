import re
import json
import os
import base64
import tempfile
from google import genai
from google.genai import types
from tacek.config import API_KEY, GEMINI_MODEL, GROQ_API_KEY
from tacek.logger import log

_client = genai.Client(api_key=API_KEY)

_groq_client = None
if GROQ_API_KEY:
    try:
        from openai import OpenAI
        _groq_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY,
        )
    except ImportError:
        log("WARNING: openai package not installed, Groq fallback disabled.")

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
- protein_g, carbs_g, fat_g, calories_kcal are estimated integers"""

_JSON_CONFIG = types.GenerateContentConfig(response_mime_type="application/json")

_GROQ_TEXT_MODEL  = "llama-3.3-70b-versatile"
_GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def _parse(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    return json.loads(text.strip())


def _groq_text(text, source_name):
    if not _groq_client:
        return None
    try:
        log(f"Trying Groq fallback for {source_name}...")
        resp = _groq_client.chat.completions.create(
            model=_GROQ_TEXT_MODEL,
            messages=[{"role": "user", "content": JSON_PROMPT + f"\n\nHere is the menu text from {source_name}:\n{text}"}],
            response_format={"type": "json_object"},
        )
        return _parse(resp.choices[0].message.content)
    except Exception as e:
        log(f"ERROR: Groq text fallback failed for {source_name}: {e}")
        return None


def _groq_image(image_path):
    if not _groq_client:
        return None
    try:
        log(f"Trying Groq vision fallback for {image_path}...")
        with open(image_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(image_path)[1].lower().lstrip('.')
        mime = f"image/{ext}" if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp') else "image/jpeg"
        resp = _groq_client.chat.completions.create(
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
        return _parse(resp.choices[0].message.content)
    except Exception as e:
        log(f"ERROR: Groq vision fallback failed for {image_path}: {e}")
        return None


def analyze_pdf(pdf_path):
    try:
        uploaded = _client.files.upload(file=pdf_path)
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[JSON_PROMPT, uploaded],
            config=_JSON_CONFIG,
        )
        return _parse(response.text)
    except Exception as e:
        log(f"WARNING: Gemini file API failed for {pdf_path}: {e}")
        log("Falling back to image rendering...")
        return _analyze_pdf_as_images(pdf_path)


def _analyze_pdf_as_images(pdf_path):
    try:
        import fitz
    except ImportError:
        log("ERROR: pymupdf not installed, cannot render PDF as images.")
        return None
    try:
        doc = fitz.open(pdf_path)
        merged = {'days': []}
        with tempfile.TemporaryDirectory() as tmp:
            for i, page in enumerate(doc):
                img_path = os.path.join(tmp, f"page_{i}.png")
                page.get_pixmap(dpi=200).save(img_path)
                data = analyze_image(img_path)
                if data:
                    merged['days'].extend(data.get('days', []))
        if merged['days']:
            return merged
        log("Image analysis returned no data, trying text extraction...")
        return _analyze_pdf_as_text(doc, pdf_path)
    except Exception as e:
        log(f"ERROR rendering PDF as images {pdf_path}: {e}")
        return None


def _analyze_pdf_as_text(doc, pdf_path):
    try:
        text = '\n'.join(page.get_text() for page in doc).strip()
        if len(text) < 50:
            log("PDF text extraction yielded too little text.")
            return None
        log(f"Extracted {len(text)} chars from PDF, sending to Gemini as text...")
        return analyze_text(text, os.path.basename(pdf_path))
    except Exception as e:
        log(f"ERROR extracting text from PDF {pdf_path}: {e}")
        return None


def analyze_text(text, source_name):
    prompt = JSON_PROMPT + f"\n\nHere is the menu text from {source_name}:\n{text}"
    try:
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=_JSON_CONFIG,
        )
        return _parse(response.text)
    except Exception as e:
        log(f"ERROR parsing {source_name} with Gemini: {e}")
        return _groq_text(text, source_name)


def analyze_image(image_path):
    log(f"Analyzing image with Gemini: {image_path}")
    result = None
    try:
        uploaded = _client.files.upload(file=image_path)
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[JSON_PROMPT, uploaded],
            config=_JSON_CONFIG,
        )
        result = _parse(response.text)
    except Exception as e:
        log(f"ERROR analyzing image {image_path} with Gemini: {e}")

    if not result or not result.get('days'):
        result = _groq_image(image_path)

    return result
