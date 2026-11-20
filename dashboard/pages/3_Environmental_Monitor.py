import streamlit as st, pandas as pd
import plotly.express as px
from api_client import api_get,api_post,show_error
from style import apply_style,header
c1,c2=st.columns(2)
if c1.button('Fetch latest Open-Meteo observations'): st.json(api_post('/api/v1/data/refresh'))
if c2.button('Fetch nearby OpenAQ PM readings'): st.json(api_post('/api/v1/data/refresh/air-quality'))
data=api_get('/api/v1/environment',params={'limit':300})
if show_error(data): st.stop()
if data:
    df=pd.DataFrame(data); df['observed_at']=pd.to_datetime(df['observed_at']); c1,c2,c3=st.columns(3); c1.metric('Latest temperature',f"{df.iloc[0]['temperature_c']} °C"); c2.metric('Latest PM2.5',str(df.iloc[0]['pm25'])); c3.metric('Real API rows',int((df['source']=='REAL_API').sum()))
    st.plotly_chart(px.line(df.sort_values('observed_at'),x='observed_at',y='temperature_c',color='zone_id',template='plotly_white',title='Temperature observations'),use_container_width=True)
    pollutants=df.dropna(subset=['pm25'])
    if not pollutants.empty: st.plotly_chart(px.line(pollutants.sort_values('observed_at'),x='observed_at',y='pm25',color='zone_id',template='plotly_white',title='PM2.5 observations (µg/m³)'),use_container_width=True)
    st.dataframe(df.head(100),use_container_width=True,hide_index=True)
else: st.info('No environmental observations yet.')
st.caption('PM2.5/PM10 are pollutant concentrations. They are not the same thing as official AQI values.')
