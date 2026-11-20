import streamlit as st
from api_client import api_get, api_post
from style import apply_style

st.set_page_config(page_title='Swasthya Sentinel', page_icon='🛡️', layout='wide', initial_sidebar_state='expanded')
apply_style()

ROLE_PAGES = {
    'district_admin': [
        ('Portal Home', '🏠', 'pages/0_Portal_Home.py'),
        ('Data Input & Ingestion', '📥', 'pages/1_Data_Input_Ingestion.py'),
        ('Geographic Intelligence', '🗺️', 'pages/2_Geographic_Intelligence.py'),
        ('Environmental Monitor', '🌦️', 'pages/3_Environmental_Monitor.py'),
        ('Population & Workforce Health', '🏥', 'pages/4_Population_Workforce_Health.py'),
        ('AI Risk Intelligence', '🧠', 'pages/5_AI_Risk_Intelligence.py'),
        ('Alert & Prevention Centre', '🚨', 'pages/6_Alert_Prevention_Centre.py'),
        ('Emergency Simulation Lab', '🧪', 'pages/7_Emergency_Simulation.py'),
        ('Validation & Performance', '📊', 'pages/8_Validation.py'),
        ('Privacy & Audit', '🔐', 'pages/9_Privacy_Audit.py'),
        ('User Management', '👥', 'pages/10_User_Management.py'),
    ],
    'health_officer': [
        ('Portal Home', '🏠', 'pages/0_Portal_Home.py'),
        ('Submit Health Data', '📥', 'pages/1_Data_Input_Ingestion.py'),
        ('Population & Workforce Health', '🏥', 'pages/4_Population_Workforce_Health.py'),
        ('AI Risk Intelligence', '🧠', 'pages/5_AI_Risk_Intelligence.py'),
        ('Alert & Prevention Centre', '🚨', 'pages/6_Alert_Prevention_Centre.py'),
    ],
    'environmental_officer': [
        ('Portal Home', '🏠', 'pages/0_Portal_Home.py'),
        ('Submit Environmental Data', '📥', 'pages/1_Data_Input_Ingestion.py'),
        ('Geographic Intelligence', '🗺️', 'pages/2_Geographic_Intelligence.py'),
        ('Environmental Monitor', '🌦️', 'pages/3_Environmental_Monitor.py'),
        ('AI Risk Intelligence', '🧠', 'pages/5_AI_Risk_Intelligence.py'),
        ('Alert & Prevention Centre', '🚨', 'pages/6_Alert_Prevention_Centre.py'),
    ],
    'workplace_safety_officer': [
        ('Portal Home', '🏠', 'pages/0_Portal_Home.py'),
        ('Submit Workplace Data', '📥', 'pages/1_Data_Input_Ingestion.py'),
        ('Population & Workforce Health', '🏥', 'pages/4_Population_Workforce_Health.py'),
        ('AI Risk Intelligence', '🧠', 'pages/5_AI_Risk_Intelligence.py'),
        ('Alert & Prevention Centre', '🚨', 'pages/6_Alert_Prevention_Centre.py'),
    ],
}


def login_screen():
    left, right = st.columns([1.15, 0.85], gap='large')
    with left:
        st.markdown('<div class="ss-eyebrow">DISTRICT HEALTH INTELLIGENCE PLATFORM</div>', unsafe_allow_html=True)
        st.title('🛡️ Swasthya Sentinel')
        st.markdown('### Detect Early. Explain Clearly. Prevent Proactively.')
        st.write('Sign in to submit aggregated observations, monitor emerging risks and coordinate preventive action across district departments.')
        st.markdown('''
        <div class="ss-feature-list">
          <div>🌡️ <b>Heat stress early warning</b><span>Environmental and health-service signals</span></div>
          <div>🌫️ <b>Respiratory risk monitoring</b><span>Air-quality and respiratory indicators</span></div>
          <div>📥 <b>Department data submission</b><span>Guided forms, CSV and Excel imports</span></div>
          <div>🧭 <b>Explainable prevention workflow</b><span>Evidence, responsible roles and action tracking</span></div>
        </div>''', unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            st.subheader('Sign in to your department')
            with st.form('login_form', clear_on_submit=False):
                username = st.text_input('Username', placeholder='Enter your account username')
                password = st.text_input('Password', type='password', placeholder='Enter your password')
                submitted = st.form_submit_button('Sign in', type='primary', use_container_width=True)
            if submitted:
                if not username.strip() or not password:
                    st.error('Enter your username and password.')
                else:
                    result = api_post('/api/v1/auth/login', json={'username': username.strip(), 'password': password})
                    if result.get('_error'):
                        st.error('Sign-in failed. Check your credentials and confirm the backend is running.')
                    else:
                        st.session_state['access_token'] = result['access_token']
                        st.session_state['current_user'] = result['user']
                        st.rerun()
            with st.expander('Local demo accounts'):
                st.caption('These accounts are created automatically for the local hackathon demo. Change passwords and the signing secret before any wider deployment.')
                st.code('District Admin: admin / Admin@Sentinel2026\nHealth Officer: health / Health@Sentinel2026\nEnvironment Officer: environment / Env@Sentinel2026\nWorkplace Officer: workplace / Work@Sentinel2026', language='text')
        st.caption('Use aggregated data only. This prototype is decision support, not medical diagnosis.')


# Validate a previously stored session against the backend.
token = st.session_state.get('access_token')
user = None
if token:
    profile = api_get('/api/v1/auth/me')
    if profile.get('_error'):
        st.session_state.pop('access_token', None)
        st.session_state.pop('current_user', None)
    else:
        user = profile
        st.session_state['current_user'] = profile

if not user:
    login_screen()
else:
    role = user['role']
    page_specs = ROLE_PAGES.get(role, ROLE_PAGES['health_officer'])
    pages = [st.Page(path, title=title, icon=icon, default=(i == 0)) for i, (title, icon, path) in enumerate(page_specs)]
    current_page = st.navigation(pages, position='sidebar')
    with st.sidebar:
        st.markdown('---')
        st.markdown(f"**{user['display_name']}**")
        st.caption(user['role_label'])
        if st.button('Sign out', use_container_width=True):
            st.session_state.pop('access_token', None)
            st.session_state.pop('current_user', None)
            st.rerun()
        st.caption('Swasthya Sentinel · District MVP')
    current_page.run()
