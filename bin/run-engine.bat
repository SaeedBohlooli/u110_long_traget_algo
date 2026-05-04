@echo off
setlocal EnableExtensions

REM ------------------------------------------------------------
REM run-engine.bat
REM Starts main\main.py in background and writes PID to:
REM   runtime\engine.pid
REM Usage:
REM   bin\run-engine.bat
REM   bin\run-engine.bat p110
REM ------------------------------------------------------------

REM Optional portfolio-id (default p110)
set PORTFOLIO_ID=p110"

set CMD="call ..\.venv\Scripts\activate && python ..\main\main.py --portfolio-id %PORTFOLIO_ID%"

REM Determine repo root as parent of this bin folder
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT=%%~fI"

set "CREATED_VENV=0"

REM Use an absolute venv path under the repo
set "VENV_DIR=%ROOT%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"


echo [run-engine] ROOT=%ROOT%
echo [run-engine] portfolio-id=%PORTFOLIO_ID%
echo [run-engine] VENV_DIR=%VENV_DIR%

REM ------------------------------------------------------------
REM Bootstrap venv if missing, then install requirements.txt
REM ------------------------------------------------------------

set "PY_EXE=%VENV_PY%"

cd %ROOT%

if not exist "%VENV_PY%" (
  echo [run-engine] .venv not found. Creating venv at: %VENV_DIR%
  pushd "%ROOT%" >nul
  python -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [run-engine] ERROR: failed to create venv
    popd >nul
    exit /b 1
  )
  popd >nul
  "%PY_EXE%" -m pip install --upgrade pip
  "%PY_EXE%" -m pip install -r requirements.txt
) else (
  echo [run-engine] .venv found at: %VENV_DIR%
)
echo %CMD%
cd bin
start cmd /k %CMD%
timeout /t 5



