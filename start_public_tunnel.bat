@echo off
title Voice Call Rating Public Tunnel Launcher
setlocal

echo ===================================================
echo   Starting Voice Call Rating With Public Tunnel
echo ===================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment was not found at .venv\Scripts\python.exe
    echo         Create the environment and install dependencies first.
    pause
    exit /b 1
)

if not exist "AI Call Center Platform\package.json" (
    echo [ERROR] Frontend project folder was not found.
    pause
    exit /b 1
)

set "CLOUDFLARED_CMD=cloudflared"
where /q cloudflared
if errorlevel 1 (
    if exist "cloudflared.exe" (
        set "CLOUDFLARED_CMD=%CD%\cloudflared.exe"
    ) else (
        echo [ERROR] cloudflared was not found in PATH and cloudflared.exe is not in the project root.
        echo         Install cloudflared globally or keep cloudflared.exe in D:\voic call rating.
        pause
        exit /b 1
    )
)

if not exist ".env" (
    echo [WARNING] No .env file found.
    echo           The backend will fall back to development defaults.
    echo           Copy .env.example to .env for a stable setup.
    echo.
)

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if not exist ".runtime\tmp" mkdir ".runtime\tmp"
set "TEMP=%CD%\.runtime\tmp"
set "TMP=%CD%\.runtime\tmp"
set "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"

echo [1/4] Starting FastAPI Backend on port 8000...
start "Backend (FastAPI)" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo [2/4] Starting Celery Worker...
timeout /t 3 /nobreak > nul
start "AI GPU Worker" cmd /k ".venv\Scripts\python.exe -m celery -A app.worker worker --loglevel=info -P solo --concurrency=1 -n gpu-worker@%%COMPUTERNAME%%"

echo [3/4] Starting React Frontend on port 5173 using proxy mode...
start "Frontend (React + Proxy)" cmd /k "cd /d ""%CD%\AI Call Center Platform"" && set ""VITE_API_BASE_URL="" && npm run dev -- --host 0.0.0.0 --port 5173 --strictPort"

echo [4/4] Starting Cloudflare Tunnel for http://localhost:5173 ...
timeout /t 6 /nobreak > nul
start "Cloudflare Tunnel" cmd /k "cd /d ""%CD%"" && ""%CLOUDFLARED_CMD%"" tunnel --url http://localhost:5173"

echo.
echo ===================================================
echo  Services are starting in separate windows.
echo.
echo  Local URLs:
echo    Frontend: http://localhost:5173
echo    Backend : http://localhost:8000
echo.
echo  IMPORTANT:
echo    1. Make sure the Frontend window says VITE ready on
echo       http://localhost:5173 before relying on the public link.
echo    2. Wait for the "Cloudflare Tunnel" window to show the public
echo       https://...trycloudflare.com URL.
echo    3. Put that URL into PUBLIC_BASE_URL inside .env if you want
echo       HR-generated interview invites to use the public link.
echo    4. Restart the backend after updating PUBLIC_BASE_URL.
echo.
echo  Example:
echo    PUBLIC_BASE_URL=https://your-name.trycloudflare.com
echo ===================================================
echo.
pause
