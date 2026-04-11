import json
import pytest
from unittest.mock import MagicMock, patch

import tacek.analyzer as analyzer


# ── _parse ────────────────────────────────────────────────────────────────────

def test_parse_clean_json():
    data = {'days': [{'day': 'Monday', 'dishes': []}]}
    assert analyzer._parse(json.dumps(data)) == data


def test_parse_strips_json_code_fence():
    data = {'days': []}
    assert analyzer._parse(f'```json\n{json.dumps(data)}\n```') == data


def test_parse_strips_bare_code_fence():
    data = {'days': []}
    assert analyzer._parse(f'```\n{json.dumps(data)}\n```') == data


def test_parse_raises_on_invalid_json():
    with pytest.raises(Exception):
        analyzer._parse('not json at all')


# ── analyze_text ─────────────────────────────────────────────────────────────

def _mock_groq_response(data):
    m = MagicMock()
    m.chat.completions.create.return_value.choices[0].message.content = json.dumps(data)
    return m


def _mock_gemini_response(data):
    m = MagicMock()
    m.models.generate_content.return_value.text = json.dumps(data)
    return m


_SAMPLE = {'days': [{'day': 'Pondělí 14.4.2026', 'dishes': [{'name': 'Svíčková'}]}]}


def test_analyze_text_groq_success():
    with patch.object(analyzer, '_groq', _mock_groq_response(_SAMPLE)):
        result = analyzer.analyze_text('menu text', 'test')
    assert result == _SAMPLE


def test_analyze_text_groq_empty_days_falls_back_to_gemini():
    mock_groq = _mock_groq_response({'days': []})
    mock_gemini = _mock_gemini_response(_SAMPLE)
    with patch.object(analyzer, '_groq', mock_groq):
        with patch.object(analyzer, '_gemini', mock_gemini):
            result = analyzer.analyze_text('menu text', 'test')
    assert result == _SAMPLE


def test_analyze_text_groq_exception_falls_back_to_gemini():
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.side_effect = Exception('rate limit')
    mock_gemini = _mock_gemini_response(_SAMPLE)
    with patch.object(analyzer, '_groq', mock_groq):
        with patch.object(analyzer, '_gemini', mock_gemini):
            result = analyzer.analyze_text('menu text', 'test')
    assert result == _SAMPLE


def test_analyze_text_no_groq_uses_gemini():
    mock_gemini = _mock_gemini_response(_SAMPLE)
    with patch.object(analyzer, '_groq', None):
        with patch.object(analyzer, '_gemini', mock_gemini):
            result = analyzer.analyze_text('menu text', 'test')
    assert result == _SAMPLE


def test_analyze_text_both_fail_returns_none():
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.side_effect = Exception('groq fail')
    mock_gemini = MagicMock()
    mock_gemini.models.generate_content.side_effect = Exception('gemini fail')
    with patch.object(analyzer, '_groq', mock_groq):
        with patch.object(analyzer, '_gemini', mock_gemini):
            result = analyzer.analyze_text('menu text', 'test')
    assert result is None


def test_analyze_text_gemini_invalid_json_returns_none():
    mock_gemini = MagicMock()
    mock_gemini.models.generate_content.return_value.text = 'not json'
    with patch.object(analyzer, '_groq', None):
        with patch.object(analyzer, '_gemini', mock_gemini):
            result = analyzer.analyze_text('menu text', 'test')
    assert result is None


# ── analyze_image ─────────────────────────────────────────────────────────────

def test_analyze_image_groq_vision_success(tmp_path):
    img = tmp_path / 'menu.jpg'
    img.write_bytes(b'\xff\xd8\xff' + b'x' * 20)
    mock_groq = _mock_groq_response(_SAMPLE)
    with patch.object(analyzer, '_groq', mock_groq):
        with patch.object(analyzer, '_downscale_image', return_value=(b'img', 'image/jpeg')):
            result = analyzer.analyze_image(str(img))
    assert result == _SAMPLE


def test_analyze_image_groq_fail_falls_back_to_gemini(tmp_path):
    img = tmp_path / 'menu.jpg'
    img.write_bytes(b'\xff\xd8\xff' + b'x' * 20)
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.side_effect = Exception('groq down')
    mock_gemini = MagicMock()
    mock_gemini.files.upload.return_value = MagicMock()
    mock_gemini.models.generate_content.return_value.text = json.dumps(_SAMPLE)
    with patch.object(analyzer, '_groq', mock_groq):
        with patch.object(analyzer, '_downscale_image', return_value=(b'img', 'image/jpeg')):
            with patch.object(analyzer, '_gemini', mock_gemini):
                result = analyzer.analyze_image(str(img))
    assert result == _SAMPLE


def test_analyze_image_no_groq_uses_gemini(tmp_path):
    img = tmp_path / 'menu.jpg'
    img.write_bytes(b'\xff\xd8\xff' + b'x' * 20)
    mock_gemini = MagicMock()
    mock_gemini.files.upload.return_value = MagicMock()
    mock_gemini.models.generate_content.return_value.text = json.dumps(_SAMPLE)
    with patch.object(analyzer, '_groq', None):
        with patch.object(analyzer, '_gemini', mock_gemini):
            result = analyzer.analyze_image(str(img))
    assert result == _SAMPLE


# ── analyze_pdf ──────────────────────────────────────────────────────────────

def test_analyze_pdf_gemini_file_api_success(tmp_path):
    pdf = tmp_path / 'menu.pdf'
    pdf.write_bytes(b'%PDF-1.4 fake content')
    mock_gemini = MagicMock()
    mock_gemini.files.upload.return_value = MagicMock()
    mock_gemini.models.generate_content.return_value.text = json.dumps(_SAMPLE)
    with patch.object(analyzer, '_gemini', mock_gemini):
        with patch.object(analyzer, '_resave_pdf', return_value=str(pdf)):
            result = analyzer.analyze_pdf(str(pdf))
    assert result == _SAMPLE


def test_analyze_pdf_falls_back_to_image_render(tmp_path):
    pdf = tmp_path / 'menu.pdf'
    pdf.write_bytes(b'%PDF-1.4 fake')
    mock_gemini = MagicMock()
    mock_gemini.files.upload.side_effect = Exception('upload failed')
    with patch.object(analyzer, '_gemini', mock_gemini):
        with patch.object(analyzer, '_resave_pdf', return_value=str(pdf)):
            with patch.object(analyzer, '_analyze_pdf_as_images', return_value=_SAMPLE):
                result = analyzer.analyze_pdf(str(pdf))
    assert result == _SAMPLE


def test_analyze_pdf_falls_back_to_text(tmp_path):
    pdf = tmp_path / 'menu.pdf'
    pdf.write_bytes(b'%PDF-1.4 fake')
    mock_gemini = MagicMock()
    mock_gemini.files.upload.side_effect = Exception('upload failed')
    with patch.object(analyzer, '_gemini', mock_gemini):
        with patch.object(analyzer, '_resave_pdf', return_value=str(pdf)):
            with patch.object(analyzer, '_analyze_pdf_as_images', return_value=None):
                with patch.object(analyzer, '_analyze_pdf_as_text', return_value=_SAMPLE):
                    result = analyzer.analyze_pdf(str(pdf))
    assert result == _SAMPLE


def test_analyze_pdf_all_strategies_fail_returns_none(tmp_path):
    pdf = tmp_path / 'menu.pdf'
    pdf.write_bytes(b'%PDF-1.4 fake')
    mock_gemini = MagicMock()
    mock_gemini.files.upload.side_effect = Exception('upload failed')
    with patch.object(analyzer, '_gemini', mock_gemini):
        with patch.object(analyzer, '_resave_pdf', return_value=str(pdf)):
            with patch.object(analyzer, '_analyze_pdf_as_images', return_value=None):
                with patch.object(analyzer, '_analyze_pdf_as_text', return_value=None):
                    result = analyzer.analyze_pdf(str(pdf))
    assert result is None
