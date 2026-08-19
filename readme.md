# SLA Monitoring Dashboard

A small end-to-end system that ingests health-check monitoring data from CSV
files, cleans and normalizes it, computes 15-minute SLA availability slots
per service, stores everything in PostgreSQL, and exposes the results
through a FastAPI backend and a static HTML/JS dashboard.

## How it works

Monitoring agents periodically hit each service and log the result
(HTTP status code, latency, agent, region, timestamp). This project turns
those raw logs into an SLA report:

```
CSV files (data/)
      │
      ▼
validation.py     → checks required columns, reports bad status codes,
                     bad latency, duplicates, inconsistent service names
      │
      ▼
normalization.py  → converts all timestamps to UTC, converts all
                     latency values to milliseconds
      │
      ▼
cleaning.py       → drops exact duplicate rows, flags (does not drop)
                     invalid status codes and negative latency
      │
      ▼
sla.py            → builds an expected 15-minute timeline per service
                     and classifies every slot as
                     available / failed / missing
      │
      ▼
db.py             → persists uploads, services, monitoring_logs and
                     sla_slots into PostgreSQL
      │
      ▼
main.py (FastAPI) → serves /api/summary, /api/services, /api/logs
      │
      ▼
frontend/         → static dashboard that calls the API and renders
                     charts/tables in the browser
```

### SLA slot classification

Data is bucketed into 15-minute windows per service (`SLOT_FREQUENCY =
"15min"` in `backend/sla.py`). For each window:

- **available** – at least one valid observation and zero failures
- **failed** – at least one valid observation and at least one failure
- **missing** – no observation was recorded for that window at all

Availability = `available_slots / expected_slots * 100`, compared against
an SLA target of **99.9%**.

## Project structure

```
Assignment/
├── backend/
│   ├── main.py              # FastAPI app: /health, /api/summary,
│   │                         #   /api/services, /api/logs
│   ├── database.py          # DB connection used by the API (main.py)
│   ├── db.py                # DB connection + insert/update helpers
│   │                         #   used by the ingestion pipeline
│   ├── validation.py        # Column/data quality checks + CSV loader
│   ├── normalization.py     # Timestamp → UTC, latency → ms
│   ├── cleaning.py          # Duplicate removal, status/latency flags
│   ├── sla.py                # Expected timeline + slot classification
│   │                         #   + SLA metrics (standalone/CLI version)
│   ├── ingest.py             # Orchestrates the full pipeline and
│   │                         #   writes results to the database
│   ├── profile_dataset.py   # Quick CLI data profiling report
│   ├── t_db.py               # Standalone DB connectivity smoke test
│   └── requirements.txt
├── data/                     # Source CSV files (health-check logs)
├── frontend/
│   ├── index.html
│   ├── app.js                # Calls the API and renders the dashboard
│   └── style.css
├── sql/
│   └── schema.sql            # uploads, services, monitoring_logs,
│                             #   sla_slots tables + indexes
└── .env                      # DATABASE_URL (not committed)
```

## Expected CSV format

Each file in `data/` must contain these columns:

| Column          | Description                                      |
|-----------------|---------------------------------------------------|
| `service_id`    | Unique service identifier                         |
| `service_name`  | Human-readable service name                        |
| `timestamp`     | ISO timestamp (with `Z`/offset) or Unix epoch      |
| `status_code`   | HTTP status code of the health check (100–599)     |
| `latency`       | Latency value                                      |
| `latency_unit`  | `ms` or `s`                                        |
| `agent`         | ID of the monitoring agent that made the request   |
| `region`        | Region the agent ran from                          |

## Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL database (local or hosted)

### 2. Install dependencies

`backend/requirements.txt` is currently empty in this repo. Install the
packages the code actually imports:

```bash
pip install fastapi uvicorn psycopg2-binary python-dotenv pandas
```

(or freeze these into `backend/requirements.txt` for reproducibility)

### 3. Configure the database

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>
```

Then create the schema:

```bash
psql "$DATABASE_URL" -f sql/schema.sql
```

You can sanity-check the connection with:

```bash
python backend/t_db.py
```

### 4. Load the data

Drop CSV files into `data/`, then run the ingestion pipeline (validates,
normalizes, cleans, computes SLA slots, and writes everything to Postgres):

```bash
python backend/ingest.py
```

Optional: inspect the raw data first without touching the database:

```bash
python backend/profile_dataset.py    # summary stats
python backend/validation.py         # data-quality report per file
```

### 5. Run the API

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://127.0.0.1:8000` (interactive docs at
`/docs`).

### 6. Open the dashboard

Serve `frontend/index.html` (e.g. with `python -m http.server` from the
`frontend/` folder, or just open it directly in a browser). It expects the
API at `http://127.0.0.1:8000` (see `API_BASE_URL` in `frontend/app.js`).

## API endpoints

| Method | Path            | Description                                              |
|--------|-----------------|------------------------------------------------------------|
| GET    | `/health`       | Checks API + database connectivity                         |
| GET    | `/`             | Basic API info                                              |
| GET    | `/api/summary`  | Overall slot counts and availability across all services   |
| GET    | `/api/services` | Per-service slot counts, availability %, and SLA status    |
| GET    | `/api/logs`     | Raw monitoring logs, filterable by `start_date`, `end_date`, `service_id`, `limit` |

## Notes / known gaps

- `backend/requirements.txt` is currently empty — see the setup section
  above for the packages that need to be installed.
- `backend/sla.py` includes its own copies of load/normalize/clean logic
  (usable as a standalone CLI script) in addition to the
  `build_slot_status` / `calculate_sla_metrics` functions that `ingest.py`
  imports and reuses.
- `backend/l_f.py` is currently an empty file.
- The frontend has an upload section, but the CSV upload endpoint isn't
  wired up yet — data currently gets into the database via
  `python backend/ingest.py` reading from the local `data/` folder.
