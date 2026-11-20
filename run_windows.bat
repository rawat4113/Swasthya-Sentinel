@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.12 and add it to PATH.
  pause
  exit /b 1
)
if not exist .venv python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error
if not exist .env copy .env.example .env
.venv\Scripts\python.exe scripts\initialize_db.py
if errorlevel 1 goto :error
start "Swasthya Sentinel API" cmd /k ""%~dp0start_backend.bat""
timeout /t 4 /nobreak >nul
start "Swasthya Sentinel Dashboard" cmd /k ""%~dp0start_dashboard.bat""
echo.
echo Backend:   http://127.0.0.1:8001
echo Swagger:   http://127.0.0.1:8001/docs
echo Dashboard: http://localhost:8501
echo.
exit /b 0
:error
echo.
echo Setup failed. Read the error above and check your Python installation and internet connection.
pause
exit /b 1
