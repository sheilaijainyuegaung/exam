@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "CHECK_ONLY=0"
if /I "%~1"=="--check" set "CHECK_ONLY=1"

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR="

for /d %%D in ("%ROOT_DIR%\*") do (
  if exist "%%~fD\package.json" (
    if /I not "%%~nxD"=="backend" (
      set "FRONTEND_DIR=%%~fD"
    )
  )
)

if not exist "%BACKEND_DIR%\app\main.py" (
  echo [ERROR] Invalid backend folder: "%BACKEND_DIR%"
  exit /b 1
)

if not defined FRONTEND_DIR (
  echo [ERROR] Frontend folder not found. Expect a top-level folder with package.json.
  exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] Invalid frontend folder: "%FRONTEND_DIR%"
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python not found in PATH
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm not found in PATH
  exit /b 1
)

if not defined DATABASE_URL set "DATABASE_URL=mysql+pymysql://root:root@127.0.0.1:3306/exam_recognition?charset=utf8mb4"
if not defined LIBREOFFICE_CMD set "LIBREOFFICE_CMD=soffice"

if "%CHECK_ONLY%"=="1" (
  echo [CHECK] OK
  echo [CHECK] ROOT_DIR=%ROOT_DIR%
  echo [CHECK] BACKEND_DIR=%BACKEND_DIR%
  echo [CHECK] FRONTEND_DIR=%FRONTEND_DIR%
  echo [CHECK] Backend command: python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
  echo [CHECK] Frontend command: npm run serve
  exit /b 0
)

echo [INFO] Starting backend in a new CMD window...
start "Exam Backend :8001" "%ComSpec%" /k "cd /d ""%BACKEND_DIR%"" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001"

echo [INFO] Starting frontend in a new CMD window...
start "Exam Frontend :8080" "%ComSpec%" /k "cd /d ""%FRONTEND_DIR%"" && npm run serve"

echo.
echo [DONE] Services started in separate windows.
echo Frontend URL: http://127.0.0.1:8080
echo Backend URL : http://127.0.0.1:8001
echo Swagger URL : http://127.0.0.1:8001/docs
echo.
echo Note: Vue may switch to 8081/8082 if 8080 is busy.
exit /b 0
