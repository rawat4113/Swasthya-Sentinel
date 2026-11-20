import streamlit as st
import pandas as pd
from api_client import api_get, show_error
from style import apply_style, header

apply_style()
user = st.session_state.get('current_user', {})
header('🏠 Department Portal', f"Welcome, {user.get('display_name', 'User')} · {user.get('role_label', 'Department user')}")
st.caption('Use this workspace to submit observations, review your submissions and follow district health intelligence.')
role = user.get('role')
messages = {
    'district_admin': ('District administration workspace', 'Manage department accounts, review all submissions, monitor alerts and access the full district intelligence suite.'),
    'health_officer': ('Health department workspace', 'Submit aggregated clinic and symptom observations, review population-health trends and follow health alerts.'),
    'environmental_officer': ('Environmental department workspace', 'Submit weather or pollution observations, review environmental monitoring and identify zone-level exposure changes.'),
    'workplace_safety_officer': ('Workplace safety workspace', 'Submit aggregated shift-level workplace observations and follow occupational health risks.'),
}
title, description = messages.get(role, ('Department workspace', 'Submit and review approved observations.'))
st.info(f'**{title}.** {description}')

if role == 'district_admin':
    overview = api_get('/api/v1/overview')
    if not show_error(overview):
        zones = overview.get('zones', [])
        cols = st.columns(4)
        cols[0].metric('Monitoring zones', len(zones))
        cols[1].metric('Active alerts', overview.get('active_alerts', 0))
        cols[2].metric('Highest heat risk', f"{max([z['heat']['score'] for z in zones], default=0):.0f}/100")
        cols[3].metric('Highest respiratory risk', f"{max([z['respiratory']['score'] for z in zones], default=0):.0f}/100")
else:
    st.markdown('#### Quick actions')
    st.write('Open **Data Input & Ingestion** from the sidebar to submit your department observations. The application validates the input and records it under your account.')

st.markdown('#### My submission history' if role != 'district_admin' else '#### Recent district submissions')
submissions = api_get('/api/v1/ingestion/my-submissions')
if not show_error(submissions):
    if submissions:
        frame = pd.DataFrame(submissions)
        columns = [c for c in ['created_at', 'created_by', 'category', 'source_type', 'filename', 'status', 'total_rows', 'imported_rows', 'invalid_rows'] if c in frame.columns]
        st.dataframe(frame[columns], use_container_width=True, hide_index=True)
    else:
        st.info('No submissions recorded yet. Your submitted observations will appear here.')

st.markdown('#### Current alerts')
alerts = api_get('/api/v1/alerts', params={'status': 'open'})
if not show_error(alerts):
    if alerts:
        st.dataframe(pd.DataFrame(alerts)[['id', 'zone_id', 'risk_type', 'severity', 'score', 'status', 'created_at']], use_container_width=True, hide_index=True)
    else:
        st.success('There are no open alerts at this time.')

st.caption('Privacy note: records are aggregated by monitoring zone and reporting period. Do not enter patient or employee identifiers.')
