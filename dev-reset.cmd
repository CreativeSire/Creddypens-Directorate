@echo off
setlocal enabledelayedexpansion

REM CreddyPens - clean dev reset
REM - Kills servers on :3000 and :8010
REM - Clears Next.js cache
REM - Starts backend + frontend in separate windows

cd /d "%~dp0"

echo.
echo [dev-reset] Killing processes on ports 3000 and 8010...

for %%P in (3000 8010) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P" ^| findstr LISTENING') do (
    echo [dev-reset] taskkill /PID %%A (port %%P)
    taskkill /F /PID %%A >nul 2>nul
  )
)

echo.
echo [dev-reset] Clearing frontend cache (.next, node_modules\.cache)...
if exist "frontend\.next" rmdir /s /q "frontend\.next"
if exist "frontend\node_modules\.cache" rmdir /s /q "frontend\node_modules\.cache"

echo.
echo [dev-reset] Starting backend (http://127.0.0.1:8010)...
start "creddypens-backend" cmd /k "cd /d \"%~dp0backend\" && python -m uvicorn app.main:app --port 8010"

echo.
echo [dev-reset] Starting frontend (http://127.0.0.1:3000)...
start "creddypens-frontend" cmd /k "cd /d \"%~dp0frontend\" && npm run dev"

echo.
echo [dev-reset] Done.

