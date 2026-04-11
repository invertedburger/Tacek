import json
import pytest
from unittest.mock import MagicMock, patch

from tacek import geocoder


def _src(domain, name='Test Restaurant'):
    return {'url': f'https://{domain}/menu', 'name': name}


def _write_cache(path, data):
    (path / 'coords.json').write_text(json.dumps(data), encoding='utf-8')


# ── cache hits ────────────────────────────────────────────────────────────────

def test_cache_hit_skips_http(tmp_path):
    _write_cache(tmp_path, {'www.example.com': [49.1, 16.6]})
    sources = [_src('www.example.com')]
    with patch.object(geocoder, 'RESULTS_DIR', str(tmp_path)):
        with patch.object(geocoder, 'RESTAURANT_NAMES', {}):
            with patch.object(geocoder, 'RESTAURANT_COORDS_OVERRIDE', {}):
                with patch('requests.get') as mock_get:
                    result = geocoder.geocode(sources)
    mock_get.assert_not_called()
    assert result[0]['coords'] == [49.1, 16.6]


def test_multiple_sources_only_fetches_uncached(tmp_path):
    _write_cache(tmp_path, {'www.cached.com': [49.0, 16.0]})
    sources = [_src('www.cached.com'), _src('www.new.com')]
    nominatim = [{'lat': '49.5', 'lon': '16.5'}]
    mock_resp = MagicMock()
    mock_resp.json.return_value = nominatim
    with patch.object(geocoder, 'RESULTS_DIR', str(tmp_path)):
        with patch.object(geocoder, 'RESTAURANT_NAMES', {}):
            with patch.object(geocoder, 'RESTAURANT_COORDS_OVERRIDE', {}):
                with patch('requests.get', return_value=mock_resp):
                    with patch('time.sleep'):
                        result = geocoder.geocode(sources)
    assert result[0]['coords'] == [49.0, 16.0]
    assert result[1]['coords'] == [49.5, 16.5]


# ── coords override ───────────────────────────────────────────────────────────

def test_coords_override_skips_http(tmp_path):
    _write_cache(tmp_path, {})
    override = {'www.iqrestaurant.cz': [49.19, 16.60]}
    sources = [_src('www.iqrestaurant.cz')]
    with patch.object(geocoder, 'RESULTS_DIR', str(tmp_path)):
        with patch.object(geocoder, 'RESTAURANT_NAMES', {}):
            with patch.object(geocoder, 'RESTAURANT_COORDS_OVERRIDE', override):
                with patch('requests.get') as mock_get:
                    result = geocoder.geocode(sources)
    mock_get.assert_not_called()
    assert result[0]['coords'] == [49.19, 16.60]


def test_coords_override_beats_cache(tmp_path):
    _write_cache(tmp_path, {'www.iqrestaurant.cz': [0.0, 0.0]})
    override = {'www.iqrestaurant.cz': [49.19, 16.60]}
    sources = [_src('www.iqrestaurant.cz')]
    with patch.object(geocoder, 'RESULTS_DIR', str(tmp_path)):
        with patch.object(geocoder, 'RESTAURANT_NAMES', {}):
            with patch.object(geocoder, 'RESTAURANT_COORDS_OVERRIDE', override):
                with patch('requests.get'):
                    result = geocoder.geocode(sources)
    assert result[0]['coords'] == [49.19, 16.60]


# ── HTTP geocoding ────────────────────────────────────────────────────────────

def test_geocode_http_success_assigns_and_caches(tmp_path):
    _write_cache(tmp_path, {})
    sources = [_src('www.new-place.cz')]
    mock_resp = MagicMock()
    mock_resp.json.return_value = [{'lat': '49.2', 'lon': '16.6'}]
    with patch.object(geocoder, 'RESULTS_DIR', str(tmp_path)):
        with patch.object(geocoder, 'RESTAURANT_NAMES', {}):
            with patch.object(geocoder, 'RESTAURANT_COORDS_OVERRIDE', {}):
                with patch('requests.get', return_value=mock_resp):
                    with patch('time.sleep'):
                        result = geocoder.geocode(sources)
    assert result[0]['coords'] == [49.2, 16.6]
    cache = json.loads((tmp_path / 'coords.json').read_text())
    assert 'www.new-place.cz' in cache


def test_geocode_empty_nominatim_response_skips_coords(tmp_path):
    _write_cache(tmp_path, {})
    sources = [_src('www.unknown.cz')]
    mock_resp = MagicMock()
    mock_resp.json.return_value = []
    with patch.object(geocoder, 'RESULTS_DIR', str(tmp_path)):
        with patch.object(geocoder, 'RESTAURANT_NAMES', {}):
            with patch.object(geocoder, 'RESTAURANT_COORDS_OVERRIDE', {}):
                with patch('requests.get', return_value=mock_resp):
                    with patch('time.sleep'):
                        result = geocoder.geocode(sources)
    assert 'coords' not in result[0]


def test_geocode_network_error_skips_coords(tmp_path):
    _write_cache(tmp_path, {})
    sources = [_src('www.broken.cz')]
    with patch.object(geocoder, 'RESULTS_DIR', str(tmp_path)):
        with patch.object(geocoder, 'RESTAURANT_NAMES', {}):
            with patch.object(geocoder, 'RESTAURANT_COORDS_OVERRIDE', {}):
                with patch('requests.get', side_effect=Exception('timeout')):
                    with patch('time.sleep'):
                        result = geocoder.geocode(sources)
    assert 'coords' not in result[0]


def test_geocode_uses_restaurant_names_for_query(tmp_path):
    _write_cache(tmp_path, {})
    names = {'www.iq.cz': 'Holandska Brno Czech Republic'}
    sources = [_src('www.iq.cz')]
    mock_resp = MagicMock()
    mock_resp.json.return_value = [{'lat': '49.2', 'lon': '16.6'}]
    with patch.object(geocoder, 'RESULTS_DIR', str(tmp_path)):
        with patch.object(geocoder, 'RESTAURANT_NAMES', names):
            with patch.object(geocoder, 'RESTAURANT_COORDS_OVERRIDE', {}):
                with patch('requests.get', return_value=mock_resp) as mock_get:
                    with patch('time.sleep'):
                        geocoder.geocode(sources)
    call_kwargs = mock_get.call_args[1]['params']
    assert call_kwargs['q'] == 'Holandska Brno Czech Republic'
