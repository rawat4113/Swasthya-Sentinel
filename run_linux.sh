#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
python scripts/initialize_db.py
python -m uvicorn app.main:app --reload --port 8001 &
API_PID=$!
sleep 3
API_BASE_URL=http://127.0.0.1:8001 python -m streamlit run dashboard/Home.py
kill "$API_PID" 2>/dev/null || true
