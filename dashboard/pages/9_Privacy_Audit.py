import streamlit as st,pandas as pd
from api_client import api_get,show_error
from style import apply_style,header
quality=api_get('/api/v1/data-quality'); audit=api_get('/api/v1/audit'); jobs=api_get('/api/v1/ingestion/jobs')
if show_error(quality) or show_error(audit) or show_error(jobs): st.stop()
st.subheader('Data inventory'); st.json(quality)
st.subheader('Import history'); st.dataframe(pd.DataFrame(jobs),use_container_width=True,hide_index=True) if jobs else st.info('No import jobs.')
st.subheader('Audit trail'); st.dataframe(pd.DataFrame(audit),use_container_width=True,hide_index=True) if audit else st.info('No audit events.')
st.info('MVP role controls are a development demonstration, not production-grade identity or access management. Small-cell suppression is a display safeguard; production deployment needs a privacy review.')
