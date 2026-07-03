@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

set "FRONTEND_PORT=7012"
set "BACKEND_PORT=7014"
set "VENV_DIR=Mi-Fitness-Sync-main\.venv"
set "BACKEND_PY=%VENV_DIR%\Scripts\python.exe"

echo ========================================
echo   Lumalog - Windows start script
echo ========================================
echo.

where npm >nul 2>nul
if errorlevel 1 (
    echo npm was not found. Please install Node.js first.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo [1/5] Installing frontend dependencies...
    pushd frontend
    call npm install
    if errorlevel 1 (
        popd
        pause
        exit /b 1
    )
    popd
) else (
    echo [1/5] Frontend dependencies OK
)

if not exist "%BACKEND_PY%" (
    echo [2/5] Creating backend virtual environment...
    where python >nul 2>nul
    if errorlevel 1 (
        echo python was not found. Please install Python 3.12 or newer first.
        pause
        exit /b 1
    )
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
    if errorlevel 1 (
        echo Python 3.12 or newer is required.
        python --version
        pause
        exit /b 1
    )
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        pause
        exit /b 1
    )
) else (
    echo [2/5] Backend virtual environment OK
    "%BACKEND_PY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
    if errorlevel 1 (
        echo The backend virtual environment uses an unsupported Python version.
        "%BACKEND_PY%" --version
        pause
        exit /b 1
    )
)

echo [3/5] Installing backend dependencies...
pushd backend
"..\%BACKEND_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    popd
    pause
    exit /b 1
)
popd

echo [4/5] Checking Playwright...
"%BACKEND_PY%" -c "from playwright.sync_api import sync_playwright; print('playwright ok')"
if errorlevel 1 (
    pause
    exit /b 1
)

set "BROWSER_FOUND=0"
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BROWSER_FOUND=1"
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BROWSER_FOUND=1"
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BROWSER_FOUND=1"
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BROWSER_FOUND=1"
if "%BROWSER_FOUND%"=="0" (
    echo Warning: Chrome or Edge was not found in the default install locations.
    echo Xiaomi two-step verification needs a local Chrome or Edge window.
)

echo [5/5] Starting development servers...
echo.
echo Backend:  http://localhost:%BACKEND_PORT%  API docs: http://localhost:%BACKEND_PORT%/docs
echo Frontend: http://localhost:%FRONTEND_PORT%
echo.

start "Lumalog Backend" cmd /k "set FRONTEND_PORT=%FRONTEND_PORT%&& set BACKEND_PORT=%BACKEND_PORT%&& cd backend && ..\%BACKEND_PY% -m uvicorn main:app --reload --reload-dir app --port %BACKEND_PORT%"
start "Lumalog Frontend" cmd /k "set FRONTEND_PORT=%FRONTEND_PORT%&& set BACKEND_PORT=%BACKEND_PORT%&& cd frontend && npm run dev -- --host 127.0.0.1 --port %FRONTEND_PORT%"

echo Both servers started. Close the two new windows to stop.
pause
