@echo off
setlocal
cd /d "%~dp0"
if /i "%~dp0"=="%USERPROFILE%\IngestControl-App\" (
  powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; $app=Join-Path $env:USERPROFILE 'IngestControl-App'; $desktop=[Environment]::GetFolderPath('DesktopDirectory'); $link=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop 'Ingest Control.lnk')); $link.TargetPath=(Join-Path $app 'ATUALIZAR_E_ABRIR_INGEST.bat'); $link.WorkingDirectory=$app; $link.Save()"
  if errorlevel 1 echo Nao foi possivel criar o atalho na area de trabalho. O Ingest abrira normalmente.
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 backend\ingest_server.py
) else (
  python backend\ingest_server.py
)
echo.
echo O servico foi encerrado. Verifique as mensagens acima.
pause
