"""
SQLite loader with upsert semantics and basic schema management.
In production this would target Redshift/Postgres via connection hook.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("WEATHER_DB_PATH", "/tmp/weather_warehouse.db"))

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS weather_observations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    city                TEXT    NOT NULL,
    latitude            REAL,
    longitude           REAL,
    obs_time            TEXT    NOT NULL,
    extracted_at        TEXT,
    loaded_at           TEXT,
    temperature_c       REAL,
    temperature_f       REAL,
    heat_index_c        REAL,
    humidity_pct        REAL,
    precipitation_mm    REAL,
    wind_speed_kmh      REAL,
    wind_speed_mph      REAL,
    wind_dir_deg        REAL,
    wind_dir_cardinal   TEXT,
    pressure_hpa        REAL,
    pressure_inhg       REAL,
    cloud_cover_pct     REAL,
    visibility_m        REAL,
    visibility_km       REAL,
    weather_code        INTEGER,
    weather_label       TEXT,
    comfort_level       TEXT,
    is_precipitation    INTEGER,
    is_low_visibility   INTEGER,
    UNIQUE(city, obs_time)
)
"""

_UPSERT = """
INSERT INTO weather_observations
    (city, latitude, longitude, obs_time, extracted_at, loaded_at,
     temperature_c, temperature_f, heat_index_c, humidity_pct,
     precipitation_mm, wind_speed_kmh, wind_speed_mph, wind_dir_deg,
     wind_dir_cardinal, pressure_hpa, pressure_inhg, cloud_cover_pct,
     visibility_m, visibility_km, weather_code, weather_label,
     comfort_level, is_precipitation, is_low_visibility)
VALUES
    (:city, :latitude, :longitude, :obs_time, :extracted_at, :loaded_at,
     :temperature_c, :temperature_f, :heat_index_c, :humidity_pct,
     :precipitation_mm, :wind_speed_kmh, :wind_speed_mph, :wind_dir_deg,
     :wind_dir_cardinal, :pressure_hpa, :pressure_inhg, :cloud_cover_pct,
     :visibility_m, :visibility_km, :weather_code, :weather_label,
     :comfort_level, :is_precipitation, :is_low_visibility)
ON CONFLICT(city, obs_time)
DO UPDATE SET
    loaded_at          = excluded.loaded_at,
    temperature_c      = excluded.temperature_c,
    temperature_f      = excluded.temperature_f,
    heat_index_c       = excluded.heat_index_c,
    humidity_pct       = excluded.humidity_pct,
    precipitation_mm   = excluded.precipitation_mm,
    wind_speed_kmh     = excluded.wind_speed_kmh,
    pressure_hpa       = excluded.pressure_hpa,
    weather_label      = excluded.weather_label,
    comfort_level      = excluded.comfort_level
"""


class WeatherLoader:
    """Handles schema creation and upsert writes to SQLite warehouse."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(_CREATE_TABLE)
            conn.commit()
        log.debug("Schema initialised at %s", self.db_path)

    def upsert_batch(self, records: list[dict]) -> dict:
        inserted = updated = errors = 0
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for rec in records:
                try:
                    cur = conn.execute(
                        "SELECT id FROM weather_observations WHERE city=? AND obs_time=?",
                        (rec["city"], rec["obs_time"])
                    )
                    exists = cur.fetchone() is not None
                    conn.execute(_UPSERT, rec)
                    if exists:
                        updated += 1
                    else:
                        inserted += 1
                except sqlite3.Error as exc:
                    log.error("DB error for %s @ %s: %s", rec.get("city"), rec.get("obs_time"), exc)
                    errors += 1
            conn.commit()
        log.info("Upsert complete — inserted=%d updated=%d errors=%d", inserted, updated, errors)
        return {"inserted": inserted, "updated": updated, "errors": errors}
