@echo off


set PROGRAM=python.exe
set PORTFOLIO=p110
set KEY_1=trading_api_service
set KEY_2=p110

set CMD="call ..\.venv\Scripts\activate && python ..\trading_api\trading_api_service.py --portfolio-id %PORTFOLIO%"

echo Starting program %CMD%
start cmd /k %CMD%
