@echo off
title Call Rating Platform Launcher
echo ===================================================
echo        Starting Call Rating Platform...
echo ===================================================
echo.

echo [1/2] Starting FastAPI Backend on port 8000...
start "Call Rating Backend (FastAPI)" cmd /k ".venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo [2/2] Starting Gradio UI on port 7860...
:: Give the backend 3 seconds to start before launching the UI
ping 127.0.0.1 -n 4 > nul
start "Call Rating UI (Gradio)" cmd /k ".venv\Scripts\python demo.py"

echo.
echo ===================================================
echo  All services have been launched in new windows!
echo  - Backend API Docs: http://localhost:8000/docs
echo  - User Interface:   http://localhost:7860
echo ===================================================
echo.
echo You can close this window now. To stop the application,
echo just close the two black windows that just opened.
pause
