import re
import json
import os
import tempfile
from google import genai
from google.genai import types
from tacek.config import API_KEY, GEMINI_MODEL

_client = genai.Client(api_key=API_KEY)

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


def _parse(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    return json.loads(text.strip())


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
        print(f"WARNING: Gemini file API failed for {pdf_path}: {e}")
        print("Falling back to image rendering...")
        return _analyze_pdf_as_images(pdf_path)


def _analyze_pdf_as_images(pdf_path):
    try:
        import fitz
    except ImportError:
        print("ERROR: pymupdf not installed, cannot render PDF as images.")
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
        return merged if merged['days'] else None
    except Exception as e:
        print(f"ERROR rendering PDF as images {pdf_path}: {e}")
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
        print(f"ERROR parsing {source_name}: {e}")
        return None


def analyze_image(image_path):
    print(f"Analyzing image with Gemini: {image_path}")
    try:
        uploaded = _client.files.upload(file=image_path)
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[JSON_PROMPT, uploaded],
            config=_JSON_CONFIG,
        )
        return _parse(response.text)
    except Exception as e:
        print(f"ERROR analyzing image {image_path}: {e}")
        return None
