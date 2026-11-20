import streamlit as st,pandas as pd
import plotly.express as px
from api_client import api_get,show_error
from style import apply_style,header
data=api_get('/api/v1/validation/summary')
if show_error(data): st.stop()
c1,c2,c3=st.columns(3); c1.metric('Environmental observations stored',data.get('stored_environment_observations',0)); c2.metric('Synthetic records evaluated',data.get('records_evaluated',0)); c3.metric('Known injected event windows',data.get('event_windows',0))
models=data.get('models',{})
if models:
    rows=[]
    for name,m in models.items(): rows.append({'Detector':name.replace('_',' ').title(),'Sensitivity':m['sensitivity'],'Positive predictive value':m['positive_predictive_value'],'False alerts / zone-week':m['false_alerts_per_zone_week'],'Mean lead time (days)':m['mean_lead_time_days']})
    df=pd.DataFrame(rows); st.subheader('Detector comparison'); st.dataframe(df,use_container_width=True,hide_index=True)
    st.plotly_chart(px.bar(df,x='Detector',y=['Sensitivity','Positive predictive value'],barmode='group',range_y=[0,1],template='plotly_white',title='Sensitivity vs positive predictive value'),use_container_width=True)
    st.plotly_chart(px.bar(df,x='Detector',y='False alerts / zone-week',template='plotly_white',title='False alert rate'),use_container_width=True)
latency=data.get('data_latency',{})
st.subheader('Data latency')
if latency.get('mean_minutes') is not None: st.metric('Mean observed-to-ingested latency (minutes)',latency['mean_minutes'],help=latency.get('note'))
else: st.info('No non-synthetic observations have been ingested yet, so operational data latency is not available.')
with st.expander('Full validation report'): st.json(data)
st.warning('The detector comparison uses reproducible synthetic event windows with known onset. These metrics demonstrate that the validation workflow calculates real measures; they are not clinical accuracy or proof of real-world health impact.')
