@echo off
echo ========================================
echo   Lumalog - 启动脚本
echo ========================================
echo.

REM Check if frontend dependencies installed
if not exist "frontend\node_modules" (
    echo [1/2] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
    echo.
) else (
    echo [1/2] Frontend dependencies OK
)

echo [2/2] Starting development servers...
echo.
set "FRONTEND_PORT=7012"
set "BACKEND_PORT=7014"

echo  Backend:  http://localhost:%BACKEND_PORT% (API docs: http://localhost:%BACKEND_PORT%/docs)
echo  Frontend: http://localhost:%FRONTEND_PORT%
echo.

set "BACKEND_PY=Mi-Fitness-Sync-main\.venv\Scripts\python.exe"
if not exist "%BACKEND_PY%" (
    echo Python 3.12+ virtual environment not found: %BACKEND_PY%
    echo Please create/install Mi-Fitness-Sync-main\.venv first.
    pause
    exit /b 1
)

start "Lumalog Backend" cmd /k "set FRONTEND_PORT=%FRONTEND_PORT%&& set BACKEND_PORT=%BACKEND_PORT%&& cd backend && ..\%BACKEND_PY% -m uvicorn main:app --reload --reload-dir app --port %BACKEND_PORT%"
start "Lumalog Frontend" cmd /k "set FRONTEND_PORT=%FRONTEND_PORT%&& set BACKEND_PORT=%BACKEND_PORT%&& cd frontend && npm run dev -- --host 127.0.0.1 --port %FRONTEND_PORT%"

echo Both servers started. Close the two new windows to stop.
pause
