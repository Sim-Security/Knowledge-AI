@echo off
setlocal enabledelayedexpansion

:: Knowledge AI Startup Script for Windows
:: This script starts both the backend and frontend services

echo.
echo ============================================================
echo.
echo    Knowledge AI - Personal Knowledge Management
echo.
echo ============================================================
echo.

set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%backend
set FRONTEND_DIR=%SCRIPT_DIR%frontend

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)

:: Setup backend
echo Setting up backend...
cd /d "%BACKEND_DIR%"

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install dependencies
echo Installing Python dependencies...
pip install -q -r requirements.txt

:: Start backend in new window
echo Starting backend server...
start "Knowledge AI Backend" cmd /k "cd /d %BACKEND_DIR% && venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000"

:: Setup frontend
echo Setting up frontend...
cd /d "%FRONTEND_DIR%"

:: Install dependencies if node_modules doesn't exist
if not exist "node_modules" (
    echo Installing Node.js dependencies...
    call npm install
)

:: Wait for backend
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

:: Start frontend in new window
echo Starting frontend server...
start "Knowledge AI Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

echo.
echo ============================================================
echo.
echo    Knowledge AI is starting!
echo.
echo    Frontend:  http://localhost:3000
echo    Backend:   http://localhost:8000
echo    API Docs:  http://localhost:8000/docs
echo.
echo    Close the terminal windows to stop the services.
echo.
echo ============================================================
echo.

:: Open browser after a delay
timeout /t 5 /nobreak >nul
start http://localhost:3000

pause
