@echo off


set "SCRIPT_DIR=%~dp0"

cd  %SCRIPT%\..\u110_long_traget_algo_ux && start cmd /k "npm run dev"

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:7102/"