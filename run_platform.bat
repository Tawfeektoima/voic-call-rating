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
echo.
echo [1/3] Starting FastAPI Backend on port 8000...
start "Backend (FastAPI)" cmd /k ".venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo [2/3] Starting Celery Workers (AI Engines)...
:: Give the backend a moment to initialize
timeout /t 3 /nobreak > nul
start "AI Worker 1" cmd /k ".venv\Scripts\celery -A app.worker worker --loglevel=info -P solo -n worker1@%%COMPUTERNAME%%"
start "AI Worker 2" cmd /k ".venv\Scripts\celery -A app.worker worker --loglevel=info -P solo -n worker2@%%COMPUTERNAME%%"

echo [3/3] Starting React Frontend on port 5173...
cd "AI Call Center Platform"
start "Frontend (React)" cmd /k "npm run dev"
cd ..

echo.
echo ===================================================
echo  All services have been launched in new windows!
echo  - Backend API:    http://localhost:8000
echo  - React Frontend: http://localhost:5173
echo  - AI Workers:     2 Workers running (Worker1 and Worker2)
echo ===================================================
echo.
echo You can close this window now. To stop the application,
echo just close the three black windows that just opened.
pause
