@echo off
setlocal ENABLEDELAYEDEXPANSION

rem CreddyPens dev reset:
rem - stops anything listening on 3000/8010
rem - clears Next.js build cache
rem - starts db + backend + frontend in separate windows

cd /d "%~dp0\.."

echo.
echo === CREDDYPENS DEV RESET ===
echo Repo: %CD%

echo.
echo [1/4] Stopping processes on ports 3000 and 8010...
call :KILLPORT 3000
call :KILLPORT 8010

echo.
echo [2/4] Clearing frontend\.next and node cache...
if exist "frontend\.next" rmdir /s /q "frontend\.next"
if exist "frontend\node_modules\.cache" rmdir /s /q "frontend\node_modules\.cache"

echo.
echo [3/4] Starting Docker services...
docker compose up -d

echo.
echo [4/4] Starting backend + frontend...
rem Use `start` to run in new windows so both processes stay alive.
start "CreddyPens Backend" cmd /k "cd /d \"%CD%\backend\" && python -m uvicorn app.main:app --port 8010"
start "CreddyPens Frontend" cmd /k "cd /d \"%CD%\frontend\" && npm run dev -- -p 3000"

echo.
echo Done. Open:
echo - http://localhost:3000
echo - http://127.0.0.1:8010/health
echo.
exit /b 0

:KILLPORT
set PORT=%~1
set PIDS=
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":%PORT% .*LISTENING"') do (
  set PIDS=!PIDS! %%p
)
if "%PIDS%"=="" (
  echo - Port %PORT%: no listener
  exit /b 0
)
for %%p in (%PIDS%) do (
  echo - Killing PID %%p on port %PORT%
  taskkill /PID %%p /F >nul 2>nul
)
exit /b 0

