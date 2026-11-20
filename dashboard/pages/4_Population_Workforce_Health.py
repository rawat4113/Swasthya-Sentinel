import streamlit as st,pandas as pd
import plotly.express as px
from api_client import api_get,show_error
from style import apply_style,header
health=api_get('/api/v1/health-signals',params={'limit':500}); work=api_get('/api/v1/workforce',params={'limit':500})
if show_error(health) or show_error(work): st.stop()

def metric_count(row, field):
    value = row.get(field)
    if pd.isna(value):
        suppressed = row.get('suppressed_fields', [])
        return 'Suppressed' if isinstance(suppressed, list) and field in suppressed else 'Unavailable'
    try:
        return f'{int(value):,}'
    except (TypeError, ValueError, OverflowError):
        return 'Unavailable'

if health:
    df=pd.DataFrame(health); df['observed_at']=pd.to_datetime(df['observed_at']); latest=df.iloc[0]
    c1,c2,c3=st.columns(3)
    c1.metric('Clinic visits (latest row)',metric_count(latest,'clinic_visits'))
    c2.metric('Heat complaints (latest)',metric_count(latest,'heat_complaints'))
    c3.metric('Respiratory complaints (latest)',metric_count(latest,'respiratory_complaints'))
    st.caption('Counts below the configured minimum group size are shown as Suppressed.')
    if df[['heat_complaints','respiratory_complaints']].notna().any().any():
        st.plotly_chart(px.line(df.sort_values('observed_at'),x='observed_at',y=['heat_complaints','respiratory_complaints'],color='zone_id',template='plotly_white',title='Aggregated health complaints (small cells suppressed)'),use_container_width=True)
    else: st.info('Complaint counts are below the configured small-cell threshold and are suppressed in this public view.')
    st.dataframe(df.head(80),use_container_width=True,hide_index=True)
if work:
    wf=pd.DataFrame(work); st.subheader('Workforce aggregates'); st.dataframe(wf.head(80),use_container_width=True,hide_index=True)
st.caption('All demo health and workforce records are synthetic aggregates. Do not infer individual employee or patient outcomes.')
