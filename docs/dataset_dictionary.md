# Dataset dictionary

## Environment observations

- `zone_id`: configured monitoring-zone key.
- `observed_at`: ISO-8601 observation timestamp.
- `temperature_c`, `humidity_pct`, `apparent_temperature_c`: weather variables.
- `aqi`: reported AQI only when provided by an AQI source; never derive it silently from pollutant concentrations.
- `pm25`, `pm10`, `no2`: pollutant concentrations in source-reported units (PM values are µg/m³ when supplied by supported data sources).
- `source_detail`: provider/station/source description supplied during import or by a connector.
- `source`: `REAL_API`, `OPENAQ`, `MANUAL`, `CSV_IMPORT`, `EXCEL_IMPORT`, or `SYNTHETIC`.

## Health observations

Aggregated counts only: clinic visits, heat complaints, respiratory complaints, fatigue reports and first-aid cases. No patient identifiers are accepted.

## Workforce observations

Aggregated by zone and shift: exposed-worker count, heat and respiratory complaints, first-aid cases and absence count. No individual employee attributes are accepted.

## Import templates

CSV templates are stored in `data/templates`. Required columns are `zone_id` and `observed_at`; remaining fields depend on the selected category. The frontend includes a source-column mapping step.

## Synthetic data

The initial demo generator creates 180 days of synthetic observations for three illustrative zones. These are not actual district, clinic or workplace records.
