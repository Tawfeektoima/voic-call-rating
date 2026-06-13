@echo off
title Voice Call Rating Platform Launcher
echo ===================================================
echo        Starting Full Platform Services...
echo ===================================================
echo.

echo [WARNING] Checking environment configuration...
if not exist .env (
    echo [ERROR] No .env file found! The app may start with SQLite by default.
    echo         Copy .env.example to .env and configure your settings.
    pause
)
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if not exist ".runtime\tmp" mkdir ".runtime\tmp"
set "TEMP=%CD%\.runtime\tmp"
set "TMP=%CD%\.runtime\tmp"
set "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"
echo.
echo [1/3] Starting FastAPI Backend on port 8000...
start "Backend (FastAPI)" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo [2/3] Starting Celery Workers (AI Engines)...
:: Give the backend a moment to initialize
timeout /t 3 /nobreak > nul
start "AI GPU Worker" cmd /k ".venv\Scripts\python.exe -m celery -A app.worker worker --loglevel=info -P solo --concurrency=1 -n gpu-worker@%%COMPUTERNAME%%"

echo [3/3] Starting React Frontend on port 5173...
cd "AI Call Center Platform"
start "Frontend (React)" cmd /k "npm run dev"
cd ..

echo.
echo ===================================================
echo  All services have been launched in new windows!
echo  - Backend API:    http://localhost:8000
echo  - React Frontend: http://localhost:5173
echo  - AI Worker:      1 GPU worker running
echo ===================================================
echo.
echo You can close this window now. To stop the application,
echo just close the black windows that just opened.
pause
