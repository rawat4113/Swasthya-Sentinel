# Swasthya Sentinel

**District-Level Multisignal Population & Workforce Health Early Warning System**  
*Detect Early. Explain Clearly. Prevent Proactively.*

Swasthya Sentinel is a runnable hackathon MVP that combines environmental observations with aggregated health-service and workplace indicators to identify emerging heat-stress and respiratory-risk patterns at district monitoring-zone level. It provides explainable anomaly scoring, separate evidence confidence, preventive-action workflows, data ingestion and scenario-based validation.

> **Important:** This is a decision-support prototype, not a medical diagnosis system or clinically validated risk model. Synthetic records are used for offline demonstration. Never upload patient identifiers or individual employee health records.

## 1. Included capabilities

- **Department application:** Login screen, signed sessions, role-specific sidebars, admin-managed accounts, per-user import history and department-scoped input permissions.
- **Connected frontend and backend:** Streamlit UI calls FastAPI endpoints; data is validated and stored by the backend.
- **Data Input & Ingestion Center:** manual forms, CSV upload, XLSX upload, GeoJSON zone upload, source-column mapping, staging preview, backend validation, approve/commit, partial import reports and import history.
- **Real environmental connectors:** Open-Meteo current weather; optional OpenAQ v3 PM2.5/PM10 connector when `OPENAQ_API_KEY` is configured. CPCB AQI values can be imported from an official CSV/API export through the environment data template.
- **Offline demo:** 180 days of synthetic aggregate data for three clearly illustrative monitoring zones.
- **Two risk pathways:** heat stress and respiratory risk.
- **AI/statistics:** rolling median/MAD robust anomaly score, EWMA utility and an Isolation Forest utility for multivariate feature rows.
- **Explainability:** calculated environmental, clinical-service and workforce weighted contributions, baseline deviation and a human-readable explanation.
- **Confidence:** separately reports freshness/availability and historical baseline sufficiency. Missing data does not lower the risk score; it lowers confidence.
- **Alerts and prevention:** duplicate/cooldown checks, evidence, recommended action, responsible role, acknowledgement and intervention tracking.
- **Simulation:** heatwave, pollution and combined scenarios are stored separately from verified observations.
- **Validation:** synthetic known-event backtest compares fixed-threshold, statistical and multisignal detectors and calculates sensitivity, PPV, false alerts per zone-week and lead time.
- **Privacy safeguards:** known personal identifier columns are rejected; low-count health/workforce outputs are suppressed by default.
- **Packaging:** Docker Compose, Windows batch launcher, Linux launcher, API docs and automated tests.

## 2. Quick start on Windows 10/11

### Option A — one-click launcher

1. Install Python 3.12 (or another supported Python version compatible with the pinned requirements).
2. Extract the ZIP.
3. Open the extracted `Swasthya-Sentinel` folder.
4. Double-click `run_windows.bat`.
5. The script creates `.venv`, installs dependencies, copies `.env.example` to `.env` if needed, initializes the database and opens two terminal windows.

Open:

- Dashboard: http://localhost:8501
- Backend: http://127.0.0.1:8001
- Swagger API documentation: http://127.0.0.1:8001/docs
- Health check: http://127.0.0.1:8001/health

### Option B — manual PowerShell setup

Open PowerShell in the extracted project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts\initialize_db.py
```

**Terminal 1 — backend:**

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8001
```

**Terminal 2 — dashboard:**

```powershell
.\.venv\Scripts\Activate.ps1
$env:API_BASE_URL="http://127.0.0.1:8001"
python -m streamlit run dashboard/Home.py
```

### Linux/macOS

```bash
chmod +x run_linux.sh
./run_linux.sh
```

### Docker Compose

```bash
docker compose up --build
```

Dashboard is on port `8501`; API is on `8001`. Docker stores `swasthya_sentinel.json` under the mounted `data` directory.


## 3. Department application sign-in

The Streamlit frontend opens with a sign-in screen. Demo accounts are created automatically when `DEMO_USERS_ENABLED=true` and the database is initialized. They are intended only for the local MVP:

| Department | Username | Demo password | Access |
|---|---|---|---|
| District Administrator | `admin` | `Admin@Sentinel2026` | All modules, account management, all submissions, simulation and approvals |
| Health Department | `health` | `Health@Sentinel2026` | Health submissions and population-health/alert views |
| Environmental Department | `environment` | `Env@Sentinel2026` | Environmental submissions, GeoJSON zones and environmental monitoring |
| Workplace Safety | `workplace` | `Work@Sentinel2026` | Aggregated workplace submissions and related health/alert views |

The administrator can create additional department accounts in **User Management**. There is no public self-registration because a user must not be able to grant themselves a privileged department role. Non-administrator accounts can see and manage only their own import jobs. Department accounts can submit only their assigned category: health, environment or workforce.

Demo credentials are intentionally seeded for a local hackathon demonstration. Change these credentials, set a long random `AUTH_SECRET_KEY`, disable demo-user seeding and deploy only behind HTTPS and appropriate infrastructure before any shared or real-world use. The included authentication is a local MVP mechanism, not a production identity-management service.

### User-facing workflow

1. Open the dashboard URL and sign in using the appropriate department account.
2. The sidebar displays only the modules permitted for that role.
3. Open **Data Submission Centre** and enter a zone-level observation or upload a CSV/XLSX file.
4. Review validation errors and approve the import.
5. The backend stores the observation, records the submitting username, recalculates the risk and creates a warning only if the multisignal alert rules are met.
6. Return to **Department Portal** to view submission history and current alerts.

The API issues an expiring signed bearer token after successful login. All dashboard data endpoints and protected write/import endpoints require that token. `GET /api/v1/auth/me` returns the current account profile. If demo account seeding is disabled for a fresh database, create the first administrator using `python scripts\create_admin.py`.

## 4. First-time data setup

`python scripts/initialize_db.py` creates the JSON data file (`swasthya_sentinel.json`) and seeds it if it is empty. The generator creates 180 days of simulated observations across three illustrative zones. To regenerate all synthetic observations (destructive to existing demo observations):

```powershell
python scripts\generate_data.py --force
```

Do not run `--force` on a data file containing records you want to keep. The JSON persistence mode is intended for a single-process local/demo deployment, not concurrent multi-worker production use.

## 5. Data ingestion workflow

Sign in to the appropriate department account, then open **Data Submission Centre** in the Streamlit sidebar.

### Manual input

The available category is determined by the signed-in department role: Health officers submit `health`, Environmental officers submit `environment`, and Workplace Safety officers submit `workforce`. District administrators can submit all three. Select a monitoring zone and enter the observation date/time and aggregate values. Submit. The backend validates and commits the record, creates an import-history record and recalculates affected zone risks.

### CSV / Excel

1. Download the category-specific CSV template from the ingestion page or use files in `data/templates/`.
2. Upload a CSV or XLSX file.
3. Map each source column to the canonical field in the UI. `zone_id` and `observed_at` are required.
4. The backend stages and validates the upload.
5. Review valid/invalid row counts and the sample preview.
6. Approve and commit valid rows. Invalid rows stay in the import error report; a partial import is labelled as such.

Naive timestamps are interpreted in the configured district timezone (`Asia/Kolkata` in the demo); timezone-aware ISO-8601 timestamps are converted to UTC for storage. Include a timezone offset when uploading records collected outside the configured district timezone.

Canonical categories and important fields:

- **environment:** `zone_id`, `observed_at`, `temperature_c`, `humidity_pct`, `apparent_temperature_c`, `aqi`, `pm25`, `pm10`, `no2`.
- **health:** `zone_id`, `observed_at`, `clinic_visits`, `heat_complaints`, `respiratory_complaints`, `fatigue_reports`, `first_aid_cases`.
- **workforce:** `zone_id`, `observed_at`, `shift`, `exposed_workers`, `heat_complaints`, `respiratory_complaints`, `first_aid_cases`, `absence_count`.

Imports are limited to 10 MB and 10,000 rows per file. The backend rejects known personal identifier columns, unknown zones, invalid dates, invalid numeric values and duplicate zone/timestamp records. Raw uploads are not silently written to observation tables.

### GeoJSON

Upload a GeoJSON `FeatureCollection` with polygon or point features. Each feature should include `properties.zone_id` and `properties.name`. The importer stores zone centroids and keeps the imported FeatureCollection for map rendering. Verify official district and zone boundaries before any real operational use.

## 6. Environmental APIs

### Open-Meteo

No API key is required for the supported forecast endpoint. Go to **Environmental Monitor** and choose the weather refresh action. Current temperature, humidity and apparent temperature observations are stored as `REAL_API` records. The coordinates come from `config/district.yaml` and the configured zones.

### OpenAQ

OpenAQ v3 requires an API key. Add it to `.env`:

```env
OPENAQ_API_KEY=your_key_here
```

Restart the backend and use the OpenAQ air-quality refresh action. The connector requests nearby sensor data for PM2.5 and PM10. These values are pollutant concentrations and are **not** converted to official AQI. Nearby station availability can vary; no reading is not a zero reading.

### CPCB AQI

The environment CSV import accepts an `aqi` column. Import data from an official CPCB source/export and retain its observation timestamp and station/source metadata when preparing records. A direct CPCB API key/resource integration is not bundled because the required access/resource configuration varies; do not use fabricated AQI as a live reading.

## 7. Dashboard modules

1. **District Command Center** — zone-level overview, heat/respiratory scores, active alerts and refresh status.
2. **Data Input & Ingestion** — manual forms, CSV/XLSX mapping, GeoJSON, preview, validation, commit and import history.
3. **Geographic Intelligence** — illustrative zone map/centroids and risk comparison; uses uploaded GeoJSON when supplied.
4. **Environmental Monitor** — weather, particulate measurements, provenance and timestamps.
5. **Population & Workforce Health** — aggregated clinic/service and workforce observations.
6. **AI Risk Intelligence** — scores, separate confidence, contributions, explanation and baseline evidence.
7. **Alert & Prevention Centre** — alert acknowledgement, responsible-role assignment and intervention completion.
8. **Emergency Simulation Lab** — inject synthetic heat/pollution conditions and compare scenario results.
9. **Validation & Performance** — synthetic known-event backtest and detector comparison.
10. **Privacy & Audit** — import jobs, data inventory and audit trail.

## 8. Risk methodology and interpretation

Initial score formulas:

- Heat = `0.40 × environmental + 0.35 × health-service anomaly + 0.25 × workforce anomaly`.
- Respiratory = `0.40 × environmental + 0.35 × health-service anomaly + 0.25 × workforce anomaly`.

Each component is normalized to 0–100. Health/workforce anomaly signals use historical median and MAD robust scoring. Prototype display bands are Normal (0–29), Watch (30–49), Elevated (50–69) and High (70–100). Weights and bands are configured in `config/risk_thresholds.yaml`.

These formulas and bands are illustrative prototype parameters. They are not official medical, heat-stress, air-quality or regulatory thresholds. The respiratory environmental component uses a simple prototype normalization; it is not a substitute for official AQI computation. Use only source-provided AQI values as AQI.

Confidence is distinct from risk and is influenced by whether three independent signal families are fresh and whether a sufficient historical baseline exists. Default freshness windows are 48 hours for environment and 72 hours for health/workforce. A high-risk score with low confidence should prompt verification.

A multisignal alert is generated when risk is at least 50 and at least two signal families are available. Alerts are subject to a 12-hour cooldown for the same zone/risk/open-state combination. These are configurable prototype rules.

## 9. Simulation and backtesting

Simulation observations are stored in `simulation_runs`, and simulation-only risk assessments/alerts are marked `is_simulated`. They do not overwrite the base observation tables. The reset endpoint retains simulation history for audit rather than deleting records.

The validation page executes a deterministic synthetic event experiment with known heat and respiratory event windows. It computes sensitivity, positive predictive value, false alerts per zone-week and average lead time for fixed-threshold, statistical and multisignal detectors. Because the experiment is generated, the metrics are test-harness diagnostics, not evidence of clinical performance or real-world health impact.

## 10. Configuration

Edit `.env` for local settings. Main options:

```env
APP_ENV=development
DATABASE_FILE=./swasthya_sentinel.json
OPENAQ_API_KEY=
DATA_MODE=demo
AUTO_REFRESH_ENABLED=false
REFRESH_INTERVAL_MINUTES=30
MIN_GROUP_SIZE=10
DISTRICT_CONFIG=config/district.yaml
API_BASE_URL=http://127.0.0.1:8001
```

`AUTO_REFRESH_ENABLED=true` enables an in-process background refresh loop for Open-Meteo and configured OpenAQ. It is intended for a single-process MVP. For multi-worker production deployments, move scheduled jobs to a dedicated worker/queue to avoid duplicate polling.

Edit `config/district.yaml` to configure district and zones. The default data and GeoJSON are labelled illustrative; replace them with verified administrative boundaries and real coordinates for a target district.

## 11. Tests

Run:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Tests cover risk scoring, validation, synthetic backtesting and key API paths. External API calls are not required for the test suite.

## 12. Troubleshooting

- **Dashboard cannot connect:** ensure the API terminal is running on port 8001 and `API_BASE_URL` points to it.
- **Address already in use:** stop the old process or choose another port and update the dashboard URL.
- **PowerShell activation blocked:** use `Set-ExecutionPolicy -Scope Process Bypass` in that PowerShell session, then activate the environment.
- **Excel parser error:** install dependencies again with `pip install -r requirements.txt`.
- **No AQI/PM records:** configure OpenAQ or import a properly sourced CPCB/export CSV. Do not interpret missing observations as clean air.
- **API network errors:** the synthetic offline dataset and dashboard remain usable; live source refresh requires network access.

## 13. Production-readiness boundary

This is a hackathon MVP, not a deployable public-health service without further work. Before real deployment, replace the local MVP authentication with a production identity provider, HTTPS, encryption, secrets management, formal privacy impact assessment, data-sharing agreements, retention controls, backups, operational monitoring, robust station-to-zone geospatial matching, clinical/public-health review, validated exposure models, and independent model evaluation. Do not use it for individual employment decisions or automated medical decisions.

## License and data

This repository contains newly generated demo code and synthetic sample data. External data-source terms apply when using Open-Meteo, OpenAQ, CPCB and other providers. Review provider terms before deployment.

Official connector references: [OpenAQ API v3 documentation](https://docs.openaq.org/api), [OpenAQ API key guidance](https://docs.openaq.org/using-the-api/api-key), [OpenAQ locations endpoint](https://docs.openaq.org/api/operations/locations_get_v3_locations_get), and [OpenAQ latest measurements](https://docs.openaq.org/resources/latest).

### Map tiles and API keys

The Geographic Intelligence page uses the standard OpenStreetMap tile layer by default. It does not require a Carto account or a Carto API key. The browser needs an internet connection to retrieve map tiles. Monitoring-zone markers and GeoJSON overlays are generated by the application. The bundled demo boundaries are illustrative, not official administrative boundaries.


## Frontend theme

The dashboard uses a healthcare-style light theme with a deep-navy department navigation sidebar, teal primary actions, white KPI/cards and consistent light Plotly charts. The geographic page retains the OpenStreetMap tile layer and its monitoring-zone risk markers.
