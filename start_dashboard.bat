@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set API_BASE_URL=http://127.0.0.1:8001
python -m streamlit run dashboard/Home.py
