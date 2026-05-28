"""
Weather data transformation — unit conversions, feature engineering,
anomaly flagging, and schema normalisation.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)

# Wind direction bins
_WIND_DIRECTIONS = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                    "S","SSW","SW","WSW","W","WNW","NW","NNW"]

# WMO weather-code to human label (subset)
_WMO_LABELS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ heavy hail",
}


class WeatherTransformer:
    """Applies all transformation rules to raw weather records."""

    # ── Unit helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def celsius_to_fahrenheit(c: float) -> float:
        return round(c * 9 / 5 + 32, 2)

    @staticmethod
    def kmh_to_mph(kmh: float) -> float:
        return round(kmh * 0.621371, 2)

    @staticmethod
    def hpa_to_inhg(hpa: float) -> float:
        return round(hpa * 0.02953, 2)

    @staticmethod
    def wind_cardinal(deg: float) -> str:
        idx = round(deg / 22.5) % 16
        return _WIND_DIRECTIONS[idx]

    @staticmethod
    def heat_index(temp_c: float, humidity: float) -> float:
        """Rothfusz heat-index formula (returns Celsius)."""
        t = temp_c * 9 / 5 + 32   # work in Fahrenheit
        rh = humidity
        hi = (-42.379 + 2.04901523*t + 10.14333127*rh
              - 0.22475541*t*rh - 0.00683783*t*t
              - 0.05481717*rh*rh + 0.00122874*t*t*rh
              + 0.00085282*t*rh*rh - 0.00000199*t*t*rh*rh)
        return round((hi - 32) * 5 / 9, 2)   # back to Celsius

    @staticmethod
    def comfort_level(temp_c: float, humidity: float) -> str:
        hi = WeatherTransformer.heat_index(temp_c, humidity)
        if hi < 0:    return "Very Cold"
        if hi < 10:   return "Cold"
        if hi < 18:   return "Cool"
        if hi < 26:   return "Comfortable"
        if hi < 32:   return "Warm"
        if hi < 40:   return "Hot"
        return "Dangerously Hot"

    # ── Core transform ───────────────────────────────────────────────────────

    def transform_record(self, raw: dict) -> dict:
        """Enrich a single raw record with derived fields and alternate units."""
        temp    = raw["temperature_c"]
        humid   = raw["humidity_pct"]
        wind_d  = raw.get("wind_dir_deg", 0) or 0
        code    = raw.get("weather_code", 0) or 0

        return {
            # identifiers / timestamps
            "city":             raw["city"],
            "latitude":         raw["latitude"],
            "longitude":        raw["longitude"],
            "obs_time":         raw["obs_time"],
            "extracted_at":     raw["extracted_at"],
            "loaded_at":        datetime.utcnow().isoformat(),

            # temperature
            "temperature_c":    round(temp, 2),
            "temperature_f":    self.celsius_to_fahrenheit(temp),
            "heat_index_c":     self.heat_index(temp, humid),

            # humidity / precipitation
            "humidity_pct":         raw["humidity_pct"],
            "precipitation_mm":     raw.get("precipitation_mm") or 0.0,

            # wind
            "wind_speed_kmh":       raw.get("wind_speed_kmh") or 0.0,
            "wind_speed_mph":       self.kmh_to_mph(raw.get("wind_speed_kmh") or 0.0),
            "wind_dir_deg":         wind_d,
            "wind_dir_cardinal":    self.wind_cardinal(wind_d),

            # pressure / visibility
            "pressure_hpa":         raw.get("pressure_hpa") or 0.0,
            "pressure_inhg":        self.hpa_to_inhg(raw.get("pressure_hpa") or 0.0),
            "cloud_cover_pct":      raw.get("cloud_cover_pct") or 0,
            "visibility_m":         raw.get("visibility_m") or 0,
            "visibility_km":        round((raw.get("visibility_m") or 0) / 1000, 2),

            # derived / categorical
            "weather_code":         code,
            "weather_label":        _WMO_LABELS.get(code, f"Code {code}"),
            "comfort_level":        self.comfort_level(temp, humid),
            "is_precipitation":     (raw.get("precipitation_mm") or 0) > 0,
            "is_low_visibility":    (raw.get("visibility_m") or 10000) < 1000,
        }

    def transform_batch(self, records: list[dict]) -> list[dict]:
        transformed, errors = [], 0
        for rec in records:
            try:
                transformed.append(self.transform_record(rec))
            except Exception as exc:
                log.error("Transform failed for %s: %s", rec.get("city"), exc)
                errors += 1
        if errors:
            log.warning("%d records failed transformation", errors)
        return transformed
