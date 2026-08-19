@echo off
title Smart Traffic Challan & ANPR Surveillance System (FYP)
color 0b

echo ==============================================================================
echo        SMART TRAFFIC CHALLAN SYSTEM BY NUMBER PLATE RECOGNITION (ANPR)
echo                   Final Year Project (FYP) - 100%% Free & Local
echo ==============================================================================
echo.

cd /d "%~dp0"

IF EXIST ".venv\Scripts\python.exe" (
    echo [1/3] Python Virtual Environment Detected.
) ELSE (
    echo [1/3] Setting up Python environment...
    "%USERPROFILE%\.local\bin\uv.exe" venv ".venv" --python 3.11
    "%USERPROFILE%\.local\bin\uv.exe" pip install -r "backend\requirements.txt" --python ".venv\Scripts\python.exe"
)

echo.
echo [2/3] Starting Backend API, AI ANPR Engine ^& Live CCTV Server...
echo ------------------------------------------------------------------------------
echo Server will be available at: http://127.0.0.1:8000
echo Command Center:   http://127.0.0.1:8000/
echo Citizen Portal:   http://127.0.0.1:8000/citizen.html
echo FYP Demo Studio:  http://127.0.0.1:8000/simulate.html
echo ------------------------------------------------------------------------------
echo.

echo [3/3] Opening Dashboard in Default Browser...
start "" "http://127.0.0.1:8000"

echo.
echo Press Ctrl+C to stop the server at any time.
echo.

".venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
pause
