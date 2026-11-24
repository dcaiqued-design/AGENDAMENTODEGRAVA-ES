@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 backend\ingest_server.py
) else (
  python backend\ingest_server.py
)
echo.
echo O servico foi encerrado. Verifique as mensagens acima.
pause
