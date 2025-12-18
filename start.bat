@echo off
setlocal enabledelayedexpansion

:: Knowledge AI Startup Script for Windows
:: This script starts both the backend and frontend services

echo.
echo ============================================================
echo.
echo    Knowledge AI - Personal Knowledge Management
echo    Local-First AI for Your Documents
echo.
echo ============================================================
echo.

set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%backend
set FRONTEND_DIR=%SCRIPT_DIR%frontend

:: ============================================================
:: Check Prerequisites
:: ============================================================

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.10-3.13 from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Check Python version (need 3.10+, not 3.14+)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
echo Found Python %PYTHON_VERSION%

:: Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Node.js is not installed or not in PATH
    echo.
    echo Please install Node.js 18 or higher from:
    echo   https://nodejs.org/
    echo.
    pause
    exit /b 1
)

for /f "tokens=1" %%v in ('node --version 2^>^&1') do set NODE_VERSION=%%v
echo Found Node.js %NODE_VERSION%

:: ============================================================
:: Check Ollama (Local AI)
:: ============================================================

echo.
echo Checking Ollama (Local AI)...

set SKIP_OLLAMA=0

:: Check if Ollama is installed
ollama --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo NOTE: Ollama is not installed.
    echo.
    echo For 100%% private, local AI operation, install Ollama from:
    echo   https://ollama.com/download
    echo.
    echo Without Ollama, you'll need a cloud API key (OpenRouter, OpenAI, etc.)
    echo You can configure this in Settings after the app starts.
    echo.
    set SKIP_OLLAMA=1
    goto :SKIP_OLLAMA_CHECK
)

echo Found Ollama

:: Check if Ollama is running by pinging the API
curl -s -o nul -w "" http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 (
    echo Starting Ollama service...
    start "" /min ollama serve
    timeout /t 3 /nobreak >nul
    
    :: Check again
    curl -s -o nul http://localhost:11434/api/version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo WARNING: Could not start Ollama service automatically.
        echo Please start Ollama manually (run "ollama serve" in another terminal).
        echo.
        set SKIP_OLLAMA=1
        goto :SKIP_OLLAMA_CHECK
    )
)

echo Ollama is running

:: Check if ANY models are installed
echo.
echo Checking for installed AI models...
ollama list >nul 2>&1
for /f %%i in ('ollama list 2^>nul ^| find /c /v ""') do set MODEL_COUNT=%%i

:: Subtract 1 for header line
set /a MODEL_COUNT=%MODEL_COUNT%-1

if %MODEL_COUNT% LEQ 0 (
    echo.
    echo No AI models are installed in Ollama.
    echo.
    echo The app will detect your hardware and recommend the best models.
    echo After the app starts, go to Settings to see recommendations
    echo based on your system's RAM and GPU.
    echo.
    echo Or install models manually:
    echo   ollama pull llama3.2:1b     (small, fast, any hardware)
    echo   ollama pull llama3.2        (balanced, needs 8GB+ RAM)
    echo   ollama pull nomic-embed-text (required for search)
    echo.
    pause
) else (
    echo Found %MODEL_COUNT% installed model(s)
    
    :: Check specifically for an embedding model
    ollama list 2>nul | findstr /C:"nomic-embed-text" /C:"mxbai-embed" /C:"all-minilm" >nul
    if errorlevel 1 (
        echo.
        echo NOTE: No embedding model found. 
        echo An embedding model is required for document search.
        echo.
        echo Recommended: ollama pull nomic-embed-text
        echo.
        echo The app will prompt you to configure this in Settings.
        echo.
    )
)

:SKIP_OLLAMA_CHECK

:: ============================================================
:: Setup Backend
:: ============================================================

echo.
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

:: ============================================================
:: Setup Frontend
:: ============================================================

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

:: ============================================================
:: Done!
:: ============================================================

echo.
echo ============================================================
echo.
echo    Knowledge AI is starting!
echo.
echo    Frontend:  http://localhost:3000
echo    Backend:   http://localhost:8000
echo    API Docs:  http://localhost:8000/docs
echo.
if %SKIP_OLLAMA%==0 (
    echo    Using LOCAL AI (Ollama) - your data stays private!
) else (
    echo    Configure your AI provider in Settings.
)
echo.
echo    Close the terminal windows to stop the services.
echo.
echo ============================================================
echo.

:: Open browser after a delay
timeout /t 5 /nobreak >nul
start http://localhost:3000

pause
