# Weather Data ETL Pipeline

> Automated ETL Pipeline — Apache Airflow · Docker · Astronomer · Open-Meteo API (2025)

## Overview
A fully automated ETL pipeline that extracts real-time weather data from the Open-Meteo REST API, transforms raw JSON payloads into structured analytics-ready records, and loads them into a persistent data store — containerized with Docker and orchestrated via Apache Airflow.

## Key Features
- **Automated Scheduling** — Airflow DAGs with daily scheduling and configurable retry logic
- **Containerized Deployment** — Docker + Astronomer (Astro CLI) for reproducible, portable execution
- **Modular Task Orchestration** — Extract → Transform → Load using Airflow's TaskFlow API
- **Robust Error Handling** — XCom-based inter-task data passing with automated error recovery

## Tech Stack
| Category | Tools |
|---|---|
| Orchestration | Apache Airflow, Astronomer (Astro CLI) |
| Containerization | Docker |
| Data Source | Open-Meteo REST API |
| Language | Python |
| Data Format | JSON → Structured Records |

## Pipeline Architecture
```
Open-Meteo API
     ↓  [Extract Task]
Raw JSON Payload
     ↓  [Transform Task]
Structured Analytics-Ready Records
     ↓  [Load Task]
Persistent Data Store
```

## Project Structure
```
weather-etl-pipeline/
├── dags/
│   └── weather_etl_dag.py      # Main Airflow DAG
├── include/
│   ├── extract.py              # API extraction logic
│   ├── transform.py            # Data transformation
│   └── load.py                 # Data loading
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---
*Code will be uploaded shortly.*
