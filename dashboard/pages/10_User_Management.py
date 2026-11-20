import streamlit as st
import pandas as pd
from api_client import api_get, api_post, show_error
from style import apply_style, header

apply_style()
header('👥 User Management', 'District administrator workspace for creating and reviewing department accounts.')
st.warning('For the hackathon MVP, accounts are managed by the district administrator. Public self-registration is disabled so users cannot assign themselves privileged department roles.')
roles = {
    'District Administrator': 'district_admin',
    'Health Department Officer': 'health_officer',
    'Environmental Department Officer': 'environmental_officer',
    'Workplace Safety Officer': 'workplace_safety_officer',
}
with st.form('create_user'):
    st.subheader('Create department account')
    c1, c2 = st.columns(2)
    username = c1.text_input('Username', placeholder='e.g. health_zone2')
    display_name = c2.text_input('Full display name', placeholder='e.g. Zone 2 Health Officer')
    password = st.text_input('Temporary password (minimum 10 characters)', type='password')
    role_label = st.selectbox('Department role', list(roles))
    submitted = st.form_submit_button('Create account', type='primary')
if submitted:
    result = api_post('/api/v1/auth/users', json={
        'username': username.strip(), 'display_name': display_name.strip(),
        'password': password, 'role': roles[role_label]
    })
    if not show_error(result):
        st.success(f"Account created: {result.get('username')} ({result.get('role')})")
        st.rerun()

st.divider()
st.subheader('Registered accounts')
users = api_get('/api/v1/auth/users')
if not show_error(users):
    if users:
        frame = pd.DataFrame(users)
        st.dataframe(frame, use_container_width=True, hide_index=True)
        active_users = [u for u in users if u.get('is_active') and u['username'] != st.session_state.get('current_user', {}).get('username')]
        if active_users:
            selected = st.selectbox('Deactivate an account', [u['username'] for u in active_users])
            if st.button('Deactivate selected account', type='secondary'):
                result = api_post(f'/api/v1/auth/users/{selected}/deactivate')
                if not show_error(result):
                    st.success(f'{selected} has been deactivated.')
                    st.rerun()
    else:
        st.info('No accounts found.')
