# SignalCare — Locally Hosted Dashboard

A Flask-based clinician dashboard that merges biosignal data from multiple
pipelines (stress scoring, physiology trends, mental-health forecasts,
clustering, and survey trajectories) into a single interactive web app.

## Quick Start

```bash
# 1. Install dependencies (Python 3.9+)
pip install -r requirements.txt

# 2. Run the server
python app.py
```

Open **http://localhost:5050** in your browser.

On first launch the app automatically extracts and merges patient data from
the `backend_01_emma/` and `backend_02_sander/` source folders. The merged
JSON is cached in `data/` and only regenerated when the source files change.

## Project Structure

```
web_app/
├── app.py               Flask server — routes and API endpoints
├── data_loader.py        Extracts Sander + Emma data, merges patients
├── requirements.txt      Python dependencies
├── data/                 Auto-generated JSON cache (gitignored)
│   ├── patients.json
│   ├── survey_by_pid.json
│   └── cluster_survey.json
├── static/
│   ├── css/
│   │   └── styles.css    Dashboard styles
│   └── js/
│       └── app.js        Client-side application logic
└── templates/
    └── index.html        HTML shell served by Flask
```

## How It Works

| Layer | Role |
|-------|------|
| **data_loader.py** | Reads the raw Sander HTML and Emma JS source files, merges 49 patients into a unified schema, and writes compact JSON to `data/`. |
| **app.py** | Serves the single-page dashboard and exposes REST endpoints (`/api/patients`, `/api/survey`, `/api/cluster-survey`, `/api/notes`, `/api/codes`, `/api/uploads`). |
| **app.js** | Fetches patient data from the API on page load, renders the triage board, patient table, charts (Plotly), clinical notes, access-code manager, and patient portal. |

## Pages

- **Dashboard** — Triage board (new uploads, declining patients, review milestones) and quick stats.
- **BioSignal Monitor** — Sortable patient table with drill-down into per-patient charts (Physiology, Stress & Sleep, Mental Health, Survey) and a Summary tab.
- **Patient Directory** — All 49 patients listed with status, cluster, and alert count.
- **Patient Access** — Generate one-time access codes for patients.
- **Patient Portal** — Patients redeem a code to view their chart and upload wearable exports.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/patients` | Merged patient data |
| GET | `/api/survey` | Survey scores by patient ID |
| GET | `/api/cluster-survey` | Cluster-level survey trajectories |
| GET | `/api/notes?pid=xx` | Clinical notes (optionally filtered) |
| POST | `/api/notes` | Add a clinical note |
| DELETE | `/api/notes/<id>` | Delete a note |
| GET | `/api/codes` | Access codes |
| POST | `/api/codes` | Create an access code |
| POST | `/api/codes/<id>/revoke` | Revoke a code |
| POST | `/api/codes/<id>/redeem` | Mark a code as redeemed |
| POST | `/api/codes/purge` | Clear all codes |
| GET | `/api/uploads?pid=xx` | Patient uploads (optionally filtered) |
| POST | `/api/uploads` | Record an upload |

## Compared to merge 02 (Static HTML)

| | merge 02 | web_app |
|---|----------|---------|
| How to run | Open `.html` in browser | `python app.py` → localhost:5050 |
| Dependencies | None | Python + Flask |
| Page size | ~723 KB (data embedded) | ~16 KB (data via API) |
| File structure | Single HTML file | Separated CSS / JS / HTML / API |
| Data storage | `localStorage` | `localStorage` + server API |

Both versions show the same dashboard. Use **merge 02** for a zero-dependency
demo, and **web_app** when you want a locally hosted experience.
