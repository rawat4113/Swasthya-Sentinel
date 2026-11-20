"""Shared visual system for the Swasthya Sentinel healthcare dashboard."""

import streamlit as st


THEME_CSS = '''
<style>
/* Application canvas */
.stApp {
    background: linear-gradient(180deg, #f8fbfd 0%, #f1f6fa 100%);
    color: #173042;
}
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: rgba(248, 251, 253, 0.92); }
.block-container { max-width: 1500px; padding-top: 1.6rem; padding-bottom: 3rem; }

/* Deep-navy navigation rail */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #102b3f 0%, #173d53 100%);
    border-right: 1px solid #24495e;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] span { color: #eaf3f7; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #b8cbd5; }
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    border-radius: 10px; margin: 2px 0; color: #eaf3f7;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: rgba(255,255,255,0.12); color: #ffffff;
}
[data-testid="stSidebar"] hr { border-color: rgba(234,243,247,0.18); }
[data-testid="stSidebar"] div.stButton > button {
    background: rgba(255,255,255,0.10); color: #ffffff;
    border: 1px solid rgba(255,255,255,0.25);
}
[data-testid="stSidebar"] div.stButton > button:hover {
    background: rgba(255,255,255,0.18); border-color: #8ed4d0; color: #ffffff;
}

/* Typography and page headings */
h1, h2, h3, h4 { color: #163449; letter-spacing: -0.025em; }
p, li, label { color: #354e5e; }
.ss-eyebrow { color: #0f8587; font-size: .76rem; font-weight: 800; letter-spacing: .16em; margin-bottom: .55rem; }
.ss-subtitle { color: #617887; font-size: .96rem; margin: -.35rem 0 1rem; }

/* KPI cards */
[data-testid="stMetric"] {
    background: #ffffff; border: 1px solid #dce7ed; border-top: 3px solid #0f8b8d;
    padding: 15px 16px; border-radius: 15px;
    box-shadow: 0 5px 18px rgba(24, 55, 73, 0.055);
}
[data-testid="stMetricLabel"] { color: #637b89 !important; font-weight: 650; }
[data-testid="stMetricValue"] { color: #173b50 !important; font-weight: 750; }
[data-testid="stMetricDelta"] { font-weight: 600; }

/* Forms, cards, inputs and tables */
div[data-testid="stForm"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #dce7ed; border-radius: 16px;
}
div[data-testid="stForm"] {
    background: #ffffff; padding: 1rem 1.1rem;
    box-shadow: 0 5px 18px rgba(24, 55, 73, 0.045);
}
.stTextInput input, .stNumberInput input, .stTextArea textarea,
.stDateInput input, .stTimeInput input {
    background: #ffffff; color: #173042; border-color: #cbd9e1; border-radius: 9px;
}
[data-baseweb="select"] > div {
    background: #ffffff; border-color: #cbd9e1; border-radius: 9px; color: #173042;
}
[data-testid="stFileUploader"] section {
    background: #fbfdfe; border: 1px dashed #a9c2ce; border-radius: 13px;
}
[data-testid="stDataFrame"], [data-testid="stTable"] {
    border: 1px solid #dce7ed; border-radius: 12px; overflow: hidden;
}
div[data-testid="stAlert"] { border-radius: 12px; border: 1px solid #dce7ed; }

/* Buttons */
div.stButton > button, div.stFormSubmitButton > button {
    border-radius: 10px; font-weight: 700; min-height: 2.55rem;
    transition: all .15s ease;
}
div.stButton > button[kind="primary"],
div.stFormSubmitButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: #0f8587; border: 1px solid #0f8587; color: #ffffff;
}
div.stButton > button[kind="primary"]:hover,
div.stFormSubmitButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: #0b7074; border-color: #0b7074; color: #ffffff;
}

/* Login feature cards */
.ss-feature-list {
    display: grid; grid-template-columns: 1fr 1fr; gap: .9rem; margin-top: 1.6rem;
}
.ss-feature-list div {
    background: #ffffff; border: 1px solid #dce7ed; border-left: 3px solid #0f8b8d;
    border-radius: 13px; padding: 1rem; min-height: 105px;
    box-shadow: 0 5px 18px rgba(24,55,73,.045); color: #173b50;
}
.ss-feature-list span { display: block; color: #657d8b; font-size: .84rem; margin-top: .35rem; }
.ss-login-card {
    background: #ffffff; border: 1px solid #dce7ed; border-radius: 18px;
    padding: 1.3rem 1.2rem .5rem; box-shadow: 0 14px 40px rgba(24,55,73,.08);
}

/* Tabs and expanders */
button[data-baseweb="tab"] { color: #526d7d; font-weight: 650; }
button[data-baseweb="tab"][aria-selected="true"] { color: #087e80; }
details { border-color: #dce7ed !important; border-radius: 12px !important; }

@media (max-width: 760px) {
    .ss-feature-list { grid-template-columns: 1fr; }
    .block-container { padding-left: 1rem; padding-right: 1rem; }
}
</style>
'''


def apply_style():
    """Apply shared light healthcare styling to every Streamlit page."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def header(title, subtitle):
    st.title(title)
    st.markdown(f'<div class="ss-subtitle">{subtitle}</div>', unsafe_allow_html=True)
