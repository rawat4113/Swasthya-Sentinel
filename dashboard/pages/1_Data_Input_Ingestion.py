from pathlib import Path
import io
import pandas as pd
import streamlit as st
from api_client import api_get, api_post, show_error
from style import apply_style, header

apply_style()
user = st.session_state.get('current_user', {})
role = user.get('role', '')
allowed_categories = {
    'district_admin': ['environment', 'health', 'workforce'],
    'health_officer': ['health'],
    'environmental_officer': ['environment'],
    'workplace_safety_officer': ['workforce'],
}.get(role, [])
category_labels = {
    'environment': 'Environmental observations',
    'health': 'Population health-service observations',
    'workforce': 'Workplace safety observations',
}
header('📥 Data Submission Centre', 'Submit department observations, import files and track processing in the district health intelligence system.')
st.caption(f"Signed in as **{user.get('display_name', 'Department user')}** · {user.get('role_label', '')}")
st.warning('Submit aggregated zone-level information only. Patient identifiers and individual employee health records are not accepted.')

zones = api_get('/api/v1/zones')
if show_error(zones):
    st.stop()
zone_opts = {f"{z['name']} ({z['id']})": z['id'] for z in zones}
if not zone_opts:
    st.error('No monitoring zones are configured. Ask the district administrator to configure zones first.')
    st.stop()

base_tabs = ['Manual submission', 'CSV / Excel import', 'My submissions']
can_manage_zones = role in ('district_admin', 'environmental_officer')
tab_names = base_tabs + (['GeoJSON zones'] if can_manage_zones else [])
tab_objects = st.tabs(tab_names)
tab_manual, tab_files, tab_history = tab_objects[:3]

with tab_manual:
    st.subheader('Submit a new observation')
    if not allowed_categories:
        st.error('Your account does not have an observation submission role.')
    else:
        category = allowed_categories[0] if len(allowed_categories) == 1 else st.selectbox(
            'Observation type', allowed_categories, format_func=lambda value: category_labels[value])
        st.caption('All values must represent an aggregated zone and reporting period. Do not enter personal records.')
        with st.form('manual_observation_form', clear_on_submit=False):
            zone_id = st.selectbox('Monitoring zone', list(zone_opts.values()),
                                   format_func=lambda value: next((label for label, zid in zone_opts.items() if zid == value), value))
            observed_date = st.date_input('Observation date')
            observed_time = st.time_input('Observation time')
            observed_at = pd.Timestamp.combine(observed_date, observed_time).isoformat()
            source_detail = st.text_input('Source / reporting unit', placeholder='e.g. District clinic aggregate, CPCB station, workplace safety report')
            record = {'zone_id': zone_id, 'observed_at': observed_at, 'source_detail': source_detail}
            if category == 'environment':
                st.markdown('**Environmental measurements**')
                c1, c2, c3 = st.columns(3)
                record['temperature_c'] = c1.number_input('Temperature (°C)', min_value=-20.0, max_value=60.0, value=32.0, step=0.5)
                record['humidity_pct'] = c2.number_input('Relative humidity (%)', min_value=0.0, max_value=100.0, value=60.0, step=1.0)
                record['apparent_temperature_c'] = c3.number_input('Apparent temperature (°C)', min_value=-20.0, max_value=70.0, value=34.0, step=0.5)
                c1, c2 = st.columns(2)
                if c1.checkbox('Include source-reported AQI'):
                    record['aqi'] = c2.number_input('AQI value', min_value=0.0, max_value=1000.0, value=50.0)
                c1, c2 = st.columns(2)
                if c1.checkbox('Include particulate measurements'):
                    record['pm25'] = c2.number_input('PM2.5 (µg/m³)', min_value=0.0, value=25.0)
                    record['pm10'] = st.number_input('PM10 (µg/m³)', min_value=0.0, value=45.0)
            elif category == 'health':
                st.markdown('**Aggregated health-service observations**')
                c1, c2, c3 = st.columns(3)
                record['clinic_visits'] = c1.number_input('Clinic visits', min_value=0, value=20, step=1)
                record['heat_complaints'] = c2.number_input('Heat-related complaints', min_value=0, value=4, step=1)
                record['respiratory_complaints'] = c3.number_input('Respiratory complaints', min_value=0, value=4, step=1)
                c1, c2 = st.columns(2)
                record['fatigue_reports'] = c1.number_input('Fatigue reports', min_value=0, value=2, step=1)
                record['first_aid_cases'] = c2.number_input('First-aid cases', min_value=0, value=1, step=1)
            else:
                st.markdown('**Aggregated workplace observations**')
                c1, c2, c3 = st.columns(3)
                record['shift'] = c1.selectbox('Reporting shift', ['Day', 'Night', 'All shifts'])
                record['exposed_workers'] = c2.number_input('Exposed workers (aggregate)', min_value=0, value=100, step=1)
                record['heat_complaints'] = c3.number_input('Heat complaints', min_value=0, value=3, step=1)
                c1, c2, c3 = st.columns(3)
                record['respiratory_complaints'] = c1.number_input('Respiratory complaints', min_value=0, value=2, step=1)
                record['first_aid_cases'] = c2.number_input('First-aid cases', min_value=0, value=1, step=1)
                record['absence_count'] = c3.number_input('Aggregated absence count', min_value=0, value=3, step=1)
            confirm = st.checkbox('I confirm this submission is aggregated and contains no personal identifiers.', value=False)
            submitted = st.form_submit_button('Submit observation for processing', type='primary', use_container_width=True)
        if submitted:
            if not confirm:
                st.error('Please confirm that the submission contains aggregated data only.')
            else:
                result = api_post('/api/v1/ingestion/manual', json={'category': category, 'record': record})
                if not show_error(result):
                    st.success(f"Submission {result.get('status', 'processed')}: {result.get('imported_rows', 0)} record(s) imported.")
                    st.json(result)
                    st.info('The backend has stored the observation and recalculated the affected zone risk. Refresh the AI Risk Intelligence page to review the latest assessment.')

with tab_files:
    st.subheader('Bulk data import')
    st.caption('Download a template, choose a dataset category, map columns and inspect the backend validation report before committing.')
    template_cols = st.columns(len(allowed_categories))
    for column, kind in zip(template_cols, allowed_categories):
        template_path = Path(__file__).resolve().parents[2] / 'data' / 'templates' / f'{kind}_template.csv'
        if template_path.exists():
            column.download_button(f"Download {kind.title()} template", template_path.read_bytes(),
                                   file_name=template_path.name, mime='text/csv', use_container_width=True)
    if not allowed_categories:
        st.error('No file import permission is assigned to this account.')
    else:
        category = allowed_categories[0] if len(allowed_categories) == 1 else st.selectbox(
            'Dataset category', allowed_categories, format_func=lambda value: category_labels[value], key='file_category')
        file = st.file_uploader('Choose CSV or Excel workbook', type=['csv', 'xlsx'], key='data_file')
        if file:
            try:
                raw_frame = pd.read_csv(file) if file.name.lower().endswith('.csv') else pd.read_excel(file)
                st.markdown('**File preview**')
                st.dataframe(raw_frame.head(10), use_container_width=True, hide_index=True)
                fields = {
                    'environment': ['zone_id', 'observed_at', 'source_detail', 'temperature_c', 'humidity_pct', 'apparent_temperature_c', 'aqi', 'pm25', 'pm10', 'no2'],
                    'health': ['zone_id', 'observed_at', 'source_detail', 'clinic_visits', 'heat_complaints', 'respiratory_complaints', 'fatigue_reports', 'first_aid_cases'],
                    'workforce': ['zone_id', 'observed_at', 'source_detail', 'shift', 'exposed_workers', 'heat_complaints', 'respiratory_complaints', 'first_aid_cases', 'absence_count'],
                }[category]
                aliases = {
                    'source_detail': ['source_detail', 'provider', 'source_name', 'data_provider', 'origin'],
                    'zone_id': ['zone_id', 'zone', 'zoneid', 'area_id'],
                    'observed_at': ['observed_at', 'date', 'datetime', 'timestamp', 'observation_time'],
                    'temperature_c': ['temperature_c', 'temperature', 'temp_c', 'temp'],
                    'humidity_pct': ['humidity_pct', 'humidity', 'relative_humidity'],
                    'apparent_temperature_c': ['apparent_temperature_c', 'apparent_temperature', 'feels_like'],
                    'aqi': ['aqi', 'air_quality_index'], 'pm25': ['pm25', 'pm2_5', 'pm2.5'], 'pm10': ['pm10', 'pm_10'],
                    'clinic_visits': ['clinic_visits', 'visits', 'total_visits'], 'heat_complaints': ['heat_complaints', 'heat_cases', 'heat_reports'],
                    'respiratory_complaints': ['respiratory_complaints', 'respiratory_cases', 'breathing_complaints'],
                    'fatigue_reports': ['fatigue_reports', 'fatigue'], 'first_aid_cases': ['first_aid_cases', 'first_aid'],
                    'exposed_workers': ['exposed_workers', 'workers_exposed'], 'shift': ['shift', 'work_shift'], 'absence_count': ['absence_count', 'absences'],
                }
                source_cols = list(raw_frame.columns)
                lower_lookup = {str(c).strip().lower().replace(' ', '_'): c for c in source_cols}
                mapping = {}
                with st.form('column_mapping_form'):
                    st.markdown('**Map source columns to Swasthya Sentinel fields**')
                    for field in fields:
                        candidates = ['— skip —'] + source_cols
                        guess = next((lower_lookup[a] for a in aliases.get(field, [field]) if a in lower_lookup), '— skip —')
                        default_index = candidates.index(guess) if guess in candidates else 0
                        mapping[field] = st.selectbox(f'Map `{field}`', candidates, index=default_index, key=f'map_{category}_{field}')
                    map_submit = st.form_submit_button('Validate and stage import', type='primary')
                if map_submit:
                    if mapping.get('zone_id') == '— skip —' or mapping.get('observed_at') == '— skip —':
                        st.error('The zone_id and observed_at mappings are required.')
                    else:
                        mapped = pd.DataFrame({target: raw_frame[source] for target, source in mapping.items() if source != '— skip —'})
                        buffer = io.BytesIO()
                        if file.name.lower().endswith('.csv'):
                            mapped.to_csv(buffer, index=False)
                            endpoint = '/api/v1/ingestion/upload/csv'
                            upload_name = file.name.rsplit('.', 1)[0] + '_mapped.csv'
                            mime = 'text/csv'
                        else:
                            mapped.to_excel(buffer, index=False)
                            endpoint = '/api/v1/ingestion/upload/excel'
                            upload_name = file.name.rsplit('.', 1)[0] + '_mapped.xlsx'
                            mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        result = api_post(endpoint + '?category=' + category,
                                          files={'file': (upload_name, buffer.getvalue(), mime)})
                        if not show_error(result):
                            st.session_state['pending_result'] = result
                            st.rerun()
            except Exception as exc:
                st.error(f'Could not read this file: {exc}')

        if st.session_state.get('pending_result'):
            result = st.session_state['pending_result']
            st.subheader('Backend validation and staging result')
            c1, c2, c3, c4 = st.columns(4)
            c1.metric('Rows detected', result.get('total_rows', 0))
            c2.metric('Valid rows', result.get('valid_rows', 0))
            c3.metric('Rows with errors', result.get('invalid_rows', 0))
            c4.metric('Duplicates', result.get('duplicate_rows', 0))
            if result.get('preview'):
                st.dataframe(pd.DataFrame(result['preview']), use_container_width=True, hide_index=True)
            if result.get('errors'):
                st.warning('Review the validation results. Invalid rows will not be committed.')
                st.dataframe(pd.DataFrame([{'row': item['row'], 'errors': '; '.join(item['errors'])} for item in result['errors']]), use_container_width=True, hide_index=True)
                error_csv = pd.DataFrame([{'row': item['row'], 'errors': '; '.join(item['errors'])} for item in result['errors']]).to_csv(index=False)
                st.download_button('Download validation errors', error_csv, file_name=f"{result['job_id']}_errors.csv", mime='text/csv')
            job_id = result['job_id']
            c1, c2, c3 = st.columns(3)
            if c1.button('Revalidate', use_container_width=True):
                updated = api_post('/api/v1/ingestion/validate?job_id=' + job_id)
                if not show_error(updated):
                    st.session_state['pending_result'] = updated
                    st.rerun()
            if c2.button('Approve and import valid rows', type='primary', use_container_width=True):
                committed = api_post('/api/v1/ingestion/commit?job_id=' + job_id)
                if not show_error(committed):
                    st.success(f"Import result: {committed.get('status')} · {committed.get('imported_rows', 0)} row(s) imported.")
                    st.session_state.pop('pending_result', None)
                    st.rerun()
            if c3.button('Reject import', use_container_width=True):
                rejected = api_post('/api/v1/ingestion/reject?job_id=' + job_id)
                if not show_error(rejected):
                    st.warning('Staged import rejected. No observations from this job were committed.')
                    st.session_state.pop('pending_result', None)
                    st.rerun()

with tab_history:
    st.subheader('Submission history')
    jobs = api_get('/api/v1/ingestion/my-submissions')
    if not show_error(jobs):
        if jobs:
            frame = pd.DataFrame(jobs)
            columns = [c for c in ['created_at', 'created_by', 'category', 'source_type', 'filename', 'status', 'total_rows', 'imported_rows', 'invalid_rows'] if c in frame.columns]
            st.dataframe(frame[columns], use_container_width=True, hide_index=True)
        else:
            st.info('You have not submitted observations yet.')
    quality = api_get('/api/v1/ingestion/data-quality')
    if not show_error(quality):
        c1, c2, c3 = st.columns(3)
        c1.metric('Environment records', quality.get('environment_records', 0))
        c2.metric('Health records', quality.get('health_records', 0))
        c3.metric('Workforce records', quality.get('workforce_records', 0))

if can_manage_zones:
    with tab_objects[3]:
        st.subheader('Import monitoring-zone boundaries')
        geo = st.file_uploader('Upload GeoJSON FeatureCollection', type=['geojson', 'json'], key='geojson_upload')
        st.caption('Only district administrators and environmental officers can update the monitoring-zone geometry in this demo.')
        if geo and st.button('Validate and import GeoJSON', type='primary'):
            result = api_post('/api/v1/ingestion/upload/geojson', files={'file': (geo.name, geo.getvalue(), 'application/geo+json')})
            if not show_error(result):
                st.success('Monitoring zones imported. Verify that the boundary file is authoritative before operational use.')
                st.json(result)
