"""
Open-Meteo API extractor with retry logic, rate-limit handling,
and schema validation for weather records.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional

import requests

log = logging.getLogger(__name__)

_BASE_URL = "https://api.open-meteo.com/v1/forecast"
_VARIABLES = [
    "temperature_2m", "relative_humidity_2m", "precipitation",
    "wind_speed_10m", "wind_direction_10m", "surface_pressure",
    "cloud_cover", "visibility", "weather_code",
]
_VALID_TEMP_RANGE   = (-90, 60)
_VALID_HUMID_RANGE  = (0, 100)
_VALID_PRESS_RANGE  = (870, 1085)


class WeatherExtractor:
    """Fetches current weather from Open-Meteo with exponential-backoff retries."""

    def __init__(self, max_retries: int = 3, timeout: int = 30) -> None:
        self.max_retries = max_retries
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "WeatherETL/2.0 (data-engineering-project)"

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _get(self, params: dict, attempt: int = 1) -> dict:
        try:
            resp = self._session.get(_BASE_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response else 0
            if code == 429 and attempt <= self.max_retries:
                wait = 2 ** attempt
                log.warning("Rate limited — retrying in %ds (attempt %d)", wait, attempt)
                time.sleep(wait)
                return self._get(params, attempt + 1)
            raise
        except requests.ConnectionError:
            if attempt <= self.max_retries:
                wait = 2 ** attempt
                log.warning("Connection error — retrying in %ds (attempt %d)", wait, attempt)
                time.sleep(wait)
                return self._get(params, attempt + 1)
            raise

    # ── Public API ───────────────────────────────────────────────────────────

    def fetch_location(self, city: str, lat: float, lon: float) -> Optional[dict]:
        """Return a raw weather record dict for a single city, or None on error."""
        params = {
            "latitude": lat, "longitude": lon,
            "current": ",".join(_VARIABLES),
            "timezone": "auto",
        }
        try:
            data = self._get(params)
            cur  = data.get("current", {})
            if not cur:
                log.error("Empty current data for %s", city)
                return None
            return {
                "city": city,
                "latitude": lat,
                "longitude": lon,
                "obs_time":           cur.get("time"),
                "temperature_c":      cur.get("temperature_2m"),
                "humidity_pct":       cur.get("relative_humidity_2m"),
                "precipitation_mm":   cur.get("precipitation"),
                "wind_speed_kmh":     cur.get("wind_speed_10m"),
                "wind_dir_deg":       cur.get("wind_direction_10m"),
                "pressure_hpa":       cur.get("surface_pressure"),
                "cloud_cover_pct":    cur.get("cloud_cover"),
                "visibility_m":       cur.get("visibility"),
                "weather_code":       cur.get("weather_code"),
                "extracted_at":       datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            log.exception("Failed to fetch %s: %s", city, exc)
            return None

    def fetch_batch(self, locations: list[dict]) -> list[dict]:
        """Fetch weather for a list of {city, lat, lon} dicts."""
        results = []
        for loc in locations:
            record = self.fetch_location(loc["city"], loc["lat"], loc["lon"])
            if record:
                results.append(record)
            time.sleep(0.5)   # stay well within Open-Meteo free-tier rate limit
        log.info("Fetched %d/%d locations successfully", len(results), len(locations))
        return results

    def validate(self, record: dict) -> bool:
        """Return True if a record passes all range and completeness checks."""
        required = ["city", "obs_time", "temperature_c", "humidity_pct", "pressure_hpa"]
        for field in required:
            if record.get(field) is None:
                log.warning("Missing field '%s' in record for %s", field, record.get("city"))
                return False

        temp  = record["temperature_c"]
        humid = record["humidity_pct"]
        press = record["pressure_hpa"]

        checks = [
            (_VALID_TEMP_RANGE[0]  <= temp  <= _VALID_TEMP_RANGE[1],
             f"temperature {temp}C out of range"),
            (_VALID_HUMID_RANGE[0] <= humid <= _VALID_HUMID_RANGE[1],
             f"humidity {humid}% out of range"),
            (_VALID_PRESS_RANGE[0] <= press <= _VALID_PRESS_RANGE[1],
             f"pressure {press}hPa out of range"),
        ]
        for ok, msg in checks:
            if not ok:
                log.warning("Validation failed for %s: %s", record["city"], msg)
                return False
        return True
