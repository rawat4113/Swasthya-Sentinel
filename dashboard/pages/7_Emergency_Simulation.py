import streamlit as st
from api_client import api_get,api_post,show_error
from style import apply_style,header
zones=api_get('/api/v1/zones')
if show_error(zones): st.stop()
scenario=st.selectbox('Scenario preset',['heatwave','pollution_spike','combined_emergency','custom'])
presets={
 'heatwave':{'temp':43,'humidity':78,'apparent':50,'pm25':25,'pm10':45,'aqi':50,'heat':24,'resp':3},
 'pollution_spike':{'temp':31,'humidity':55,'apparent':32,'pm25':105,'pm10':170,'aqi':180,'heat':3,'resp':25},
 'combined_emergency':{'temp':43,'humidity':80,'apparent':51,'pm25':100,'pm10':165,'aqi':190,'heat':24,'resp':25},
 'custom':{'temp':36,'humidity':60,'apparent':38,'pm25':35,'pm10':55,'aqi':70,'heat':8,'resp':8}}
p=presets[scenario]
with st.form('scenario'):
    zid=st.selectbox('Monitoring zone',[z['id'] for z in zones])
    c1,c2,c3=st.columns(3); temp=c1.slider('Temperature °C',20,50,p['temp']); humidity=c2.slider('Humidity %',20,100,p['humidity']); apparent=c3.slider('Apparent temperature °C',20,55,p['apparent'])
    c1,c2,c3=st.columns(3); pm25=c1.slider('PM2.5 µg/m³',0,250,p['pm25']); pm10=c2.slider('PM10 µg/m³',0,400,p['pm10']); aqi=c3.slider('AQI (if supplied)',0,500,p['aqi'])
    c1,c2=st.columns(2); heat=c1.number_input('Aggregated heat complaints',0,500,p['heat']); resp=c2.number_input('Aggregated respiratory complaints',0,500,p['resp'])
    submit=st.form_submit_button('Run simulation',type='primary')
if submit:
    data={'zone_id':zid,'scenario':scenario,'temperature_c':temp,'humidity_pct':humidity,'apparent_temperature_c':apparent,'pm25':pm25,'pm10':pm10,'aqi':aqi,'heat_complaints':heat,'respiratory_complaints':resp,'workforce_heat_complaints':max(1,heat//2),'workforce_respiratory_complaints':max(1,resp//2)}
    result=api_post('/api/v1/simulation/run',json=data)
    if not show_error(result): st.success('Simulation evaluated. Results are flagged as simulated.'); st.json(result)
st.divider()
if st.button('Reset simulated alerts and assessments'):
    result=api_post('/api/v1/simulation/reset')
    if not show_error(result): st.success('Simulation outputs cleared; run history and verified observations were preserved.'); st.json(result)
st.caption('Simulation results are kept separately from verified historical input. Reset clears simulated alerts/assessments but retains run history for audit.')
