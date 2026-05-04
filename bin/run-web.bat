@echo off


set "SCRIPT_DIR=%~dp0"

echo %SCRIPT_DIR%
cd %SCRIPT_DIR%\..\..\u110_long_traget_algo_ux && start cmd /k "npm run dev"


rem start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:7102/"


