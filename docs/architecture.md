# Swasthya Sentinel architecture

Swasthya Sentinel is a district-level multisignal early-warning decision-support MVP. The Streamlit frontend calls a FastAPI backend; FastAPI validates and processes input, stores records in a readable JSON document, calculates separate heat and respiratory risk assessments, and manages alerts/interventions.

```text
Manual forms / CSV / XLSX / GeoJSON / Open-Meteo / OpenAQ / Demo data
                              |
                              v
                    FastAPI ingestion API
                              |
                 staging -> validation -> approval
                              |
                              v
              JSON document store
                              |
             feature aggregation + historical baselines
                              |
                  heat and respiratory engines
                              |
            contribution explanations + confidence score
                              |
                  alerts + prevention workflow
                              |
               Streamlit maps, charts, operations UI
```

## Risk methodology

The initial configurable risk formulas are 40% environmental, 35% health-service anomaly and 25% workforce anomaly. Robust anomaly scoring uses a historical median and median absolute deviation. This is a prototype methodology, not a medical or occupational exposure model. The dashboard displays risk separately from confidence. Missing signals reduce confidence; they do not reduce the calculated risk score.

## Signal independence

The current implementation tracks three signal families: environmental, health-service and workforce. A multisignal alert requires a score of at least 50 and at least two available families. A single environmental change should be treated as an environmental watch, not as evidence of a health event.

## Data flow

The JSON database file (`swasthya_sentinel.json` by default) contains named record collections and ID sequences. `DATABASE_FILE` can point to another JSON path. This lightweight persistence mode is intended for a single-process local/demo deployment; use a transactional database for concurrent multi-worker or production workloads.

Imports are staged as JSON rows in `ingestion_jobs`. Users preview them, the backend validates schema/zone/date/count values, and the commit endpoint writes valid rows to their corresponding observation table. Invalid rows are retained in the job error report. Duplicate zone/time observations are rejected on commit. A successful import triggers recalculation for affected zones.

## Simulation isolation

Scenario runs are stored in `simulation_runs`; simulation assessments and alerts carry `is_simulated=true`. Simulation data does not overwrite historical observation tables. The reset endpoint deliberately retains simulation history for audit and does not delete verified observations.

## Department application and access control

The browser-facing Streamlit application begins with a sign-in screen. FastAPI verifies salted PBKDF2 password hashes and issues short-lived HMAC-signed bearer tokens. The frontend stores the token in the Streamlit session and sends it on API requests. Roles are `district_admin`, `health_officer`, `environmental_officer` and `workplace_safety_officer`. Department roles can submit only their assigned observation category; non-admin users can access only their own ingestion jobs. The district administrator can create and deactivate accounts and review all submission history. API read endpoints require authentication; simulation and user administration require the district-admin role.

The seeded usernames/passwords are for local demo use only. This mechanism is an MVP security boundary and must be replaced or hardened with an identity provider and deployment controls before public or real operational use.
