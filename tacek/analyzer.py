import re
import json
import google.generativeai as genai
from tacek.config import API_KEY, GEMINI_MODEL

genai.configure(api_key=API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL)

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

_JSON_CONFIG = genai.GenerationConfig(response_mime_type="application/json")


def _parse(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    return json.loads(text.strip())


def analyze_pdf(pdf_path):
    try:
        uploaded = genai.upload_file(pdf_path)
        response = _model.generate_content([JSON_PROMPT, uploaded], generation_config=_JSON_CONFIG)
        return _parse(response.text)
    except Exception as e:
        print(f"ERROR analyzing {pdf_path}: {e}")
        return None


def analyze_text(text, source_name):
    prompt = JSON_PROMPT + f"\n\nHere is the menu text from {source_name}:\n{text}"
    response = _model.generate_content(prompt, generation_config=_JSON_CONFIG)
    try:
        return _parse(response.text)
    except Exception as e:
        print(f"ERROR parsing {source_name}: {e}\nPreview: {response.text[:300]}")
        return None


def analyze_image(image_path):
    print(f"Analyzing image with Gemini: {image_path}")
    try:
        uploaded = genai.upload_file(image_path)
        response = _model.generate_content([JSON_PROMPT, uploaded], generation_config=_JSON_CONFIG)
        return _parse(response.text)
    except Exception as e:
        print(f"ERROR analyzing image {image_path}: {e}")
        return None
