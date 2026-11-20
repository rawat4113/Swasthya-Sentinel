import streamlit as st,pandas as pd
import plotly.express as px
from api_client import api_get,show_error
from style import apply_style,header
data=api_get('/api/v1/risks')
if show_error(data): st.stop()
for item in data:
    st.subheader(item['zone_id']); cols=st.columns(2)
    for c,risk in zip(cols,item['assessments']):
        with c:
            st.metric(risk['risk_type'].title()+' risk',f"{risk['score']}/100",risk['severity']); st.progress(min(100,int(risk['confidence']))); st.caption(f"Evidence confidence: {risk['confidence']}%")
            st.write(risk['explanation']); st.json(risk['evidence'])
            contrib=pd.DataFrame(risk.get('contributions',[]))
            if not contrib.empty: st.plotly_chart(px.bar(contrib,x='contribution',y='signal',orientation='h',template='plotly_white',title='Weighted signal contributions'),use_container_width=True)
st.info('Prototype risk formulas and bands are configurable demonstration parameters, not medically validated thresholds or clinical predictions.')
