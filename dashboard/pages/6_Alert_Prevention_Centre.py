import streamlit as st,pandas as pd
from api_client import api_get,api_post,show_error
from style import apply_style,header
alerts=api_get('/api/v1/alerts')
if show_error(alerts): st.stop()
if alerts:
    st.dataframe(pd.DataFrame(alerts),use_container_width=True,hide_index=True)
    ids=[a['id'] for a in alerts]; aid=st.selectbox('Select alert ID',ids)
    alert=next(x for x in alerts if x['id']==aid)
    st.subheader(alert['title']); st.write(alert['explanation']); st.markdown('**Recommended action:** '+alert['recommendation']); st.markdown('**Responsible role:** '+alert['responsible_role'])
    c1,c2=st.columns(2)
    if c1.button('Acknowledge alert'): st.json(api_post(f'/api/v1/alerts/{aid}/acknowledge',json={'actor':'demo-user'}))
    with c2.form('action_form'):
        role=st.selectbox('Assign role',['District Health Officer','District Surveillance Officer','Occupational Health and Safety Officer','Environmental Officer','Workplace Health Officer']); notes=st.text_area('Intervention notes'); submit=st.form_submit_button('Assign preventive action')
    if submit: st.json(api_post(f'/api/v1/alerts/{aid}/actions',json={'responsible_role':role,'notes':notes}))
else: st.success('No alerts generated yet. Run an emergency simulation or import qualifying observations.')
st.divider(); st.subheader('Intervention tracking')
actions=api_get('/api/v1/actions')
if show_error(actions): st.stop()
if actions:
    st.dataframe(pd.DataFrame(actions),use_container_width=True,hide_index=True)
    pending=[x for x in actions if x['status']!='completed']
    if pending:
        selected=st.selectbox('Action to complete',[x['id'] for x in pending])
        if st.button('Mark action completed'): st.json(api_post(f'/api/v1/actions/{selected}/complete'))
else: st.info('No preventive actions assigned yet.')
