"""Unit tests for WeatherTransformer."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from include.transform import WeatherTransformer

T = WeatherTransformer()

SAMPLE = {
    "city": "Houston", "latitude": 29.76, "longitude": -95.37,
    "obs_time": "2025-06-01T06:00", "extracted_at": "2025-06-01T06:01:00",
    "temperature_c": 32.5, "humidity_pct": 75, "precipitation_mm": 0.0,
    "wind_speed_kmh": 20.0, "wind_dir_deg": 180, "pressure_hpa": 1012.5,
    "cloud_cover_pct": 40, "visibility_m": 8000, "weather_code": 2,
}


def test_fahrenheit_conversion():
    assert T.celsius_to_fahrenheit(0)   == 32.0
    assert T.celsius_to_fahrenheit(100) == 212.0
    assert T.celsius_to_fahrenheit(-40) == -40.0


def test_kmh_to_mph():
    assert T.kmh_to_mph(0)   == 0.0
    assert T.kmh_to_mph(100) == pytest.approx(62.1371, rel=1e-3)


def test_wind_cardinal():
    assert T.wind_cardinal(0)   == "N"
    assert T.wind_cardinal(90)  == "E"
    assert T.wind_cardinal(180) == "S"
    assert T.wind_cardinal(270) == "W"


def test_comfort_level():
    assert T.comfort_level(-5, 50)  == "Very Cold"
    assert T.comfort_level(22, 50)  == "Comfortable"
    assert T.comfort_level(45, 90)  == "Dangerously Hot"


def test_transform_record_keys():
    result = T.transform_record(SAMPLE)
    expected_keys = [
        "city", "temperature_c", "temperature_f", "heat_index_c",
        "wind_dir_cardinal", "weather_label", "comfort_level",
        "is_precipitation", "visibility_km", "pressure_inhg",
    ]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"


def test_transform_record_types():
    result = T.transform_record(SAMPLE)
    assert isinstance(result["temperature_f"],  float)
    assert isinstance(result["wind_dir_cardinal"], str)
    assert isinstance(result["is_precipitation"], bool)


def test_transform_batch():
    batch  = [SAMPLE, {**SAMPLE, "city": "Chicago", "temperature_c": 15.0}]
    output = T.transform_batch(batch)
    assert len(output) == 2
    assert output[0]["city"] == "Houston"
    assert output[1]["city"] == "Chicago"
