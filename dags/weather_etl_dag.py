"""
Weather Data ETL Pipeline — Apache Airflow DAG
Extracts real-time weather data from Open-Meteo API for 5 US cities,
validates, transforms, and loads into a local SQLite data warehouse.

Schedule : Daily @ 06:00 UTC
Author   : Vijaya Lakshmi Atluri
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from airflow.decorators import dag, task

log = logging.getLogger(__name__)

LOCATIONS = [
    {"city": "New York",     "lat": 40.7128, "lon": -74.0060},
    {"city": "Houston",      "lat": 29.7604, "lon": -95.3698},
    {"city": "Chicago",      "lat": 41.8781, "lon": -87.6298},
    {"city": "Los Angeles",  "lat": 34.0522, "lon": -118.2437},
    {"city": "Kansas City",  "lat": 39.0997, "lon": -94.5786},
]

DEFAULT_ARGS = {
    "owner": "vijaya-atluri",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}


@dag(
    dag_id="weather_etl_pipeline",
    default_args=DEFAULT_ARGS,
    description="Daily weather ETL: Open-Meteo API -> Transform -> SQLite",
    schedule="0 6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["etl", "weather", "data-engineering"],
    doc_md=__doc__,
)
def weather_etl_pipeline():

    @task(task_id="extract_weather_data", retries=3)
    def extract() -> list[dict]:
        from include.extract import WeatherExtractor
        extractor = WeatherExtractor()
        raw = extractor.fetch_batch(LOCATIONS)
        log.info("Extracted %d/%d locations", len(raw), len(LOCATIONS))
        return raw

    @task(task_id="validate_raw_data")
    def validate(raw: list[dict]) -> list[dict]:
        from include.extract import WeatherExtractor
        extractor = WeatherExtractor()
        valid = [r for r in raw if extractor.validate(r)]
        failed = len(raw) - len(valid)
        if failed:
            log.warning("%d records failed validation and were dropped", failed)
        if not valid:
            raise ValueError("Zero valid records — aborting pipeline run")
        return valid

    @task(task_id="transform_weather_data")
    def transform(raw: list[dict]) -> list[dict]:
        from include.transform import WeatherTransformer
        t = WeatherTransformer()
        records = t.transform_batch(raw)
        log.info("Transformed %d records", len(records))
        return records

    @task(task_id="load_to_warehouse")
    def load(records: list[dict]) -> dict:
        from include.load import WeatherLoader
        loader = WeatherLoader()
        result = loader.upsert_batch(records)
        log.info("Load complete — inserted: %d, updated: %d",
                 result["inserted"], result["updated"])
        return result

    @task(task_id="log_pipeline_summary")
    def summarise(result: dict, records: list[dict]) -> None:
        cities = ", ".join(r["city"] for r in records)
        log.info("=" * 60)
        log.info("PIPELINE SUMMARY")
        log.info("  Records processed : %d", len(records))
        log.info("  Rows inserted     : %d", result.get("inserted", 0))
        log.info("  Rows updated      : %d", result.get("updated", 0))
        log.info("  Cities covered    : %s", cities)
        log.info("=" * 60)

    raw     = extract()
    valid   = validate(raw)
    clean   = transform(valid)
    result  = load(clean)
    summarise(result, clean)


dag_instance = weather_etl_pipeline()
