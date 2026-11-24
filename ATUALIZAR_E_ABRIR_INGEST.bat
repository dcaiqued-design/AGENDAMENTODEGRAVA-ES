@echo off
setlocal
title Atualizar e abrir Ingest Control
set "INGEST_REPO=https://github.com/dcaiqued-design/AGENDAMENTODEGRAVA-ES.git"
set "INGEST_BRANCH=feat/v07-integracao-painel-azul"
set "INGEST_APP=%USERPROFILE%\IngestControl-App"
set "INGEST_GIT=git.exe"

where git.exe >nul 2>nul
if errorlevel 1 (
  if exist "%ProgramFiles%\Git\cmd\git.exe" (
    set "INGEST_GIT=%ProgramFiles%\Git\cmd\git.exe"
  ) else (
    echo Instale o Git para Windows uma vez e abra este arquivo novamente.
    start "" "https://gitforwindows.org/"
    pause
    exit /b 1
  )
)

powershell.exe -NoProfile -Command "if (([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()).Port -contains 8765) { exit 1 }"
if errorlevel 1 (
  echo Finalize as gravacoes e feche a janela anterior do Ingest antes de atualizar.
  goto failed
)

if exist "%INGEST_APP%\.git" goto update
if exist "%INGEST_APP%" (
  echo A pasta "%INGEST_APP%" ja existe. Confira essa pasta antes de continuar.
  goto failed
)
echo Preparando a pasta do Ingest Control...
"%INGEST_GIT%" clone --branch "%INGEST_BRANCH%" --single-branch "%INGEST_REPO%" "%INGEST_APP%"
if errorlevel 1 goto failed
goto prepare

:update
"%INGEST_GIT%" -C "%INGEST_APP%" pull --ff-only
if errorlevel 1 goto failed

:prepare
if exist "%~dp0tools\mediamtx\mediamtx.exe" if not exist "%INGEST_APP%\tools\mediamtx\mediamtx.exe" (
  if not exist "%INGEST_APP%\tools\mediamtx" mkdir "%INGEST_APP%\tools\mediamtx"
  if exist "%~dp0tools\mediamtx\mediamtx.yml" if not exist "%INGEST_APP%\tools\mediamtx\mediamtx.yml" copy /-y "%~dp0tools\mediamtx\mediamtx.yml" "%INGEST_APP%\tools\mediamtx\mediamtx.yml" >nul
  copy /-y "%~dp0tools\mediamtx\mediamtx.exe" "%INGEST_APP%\tools\mediamtx\mediamtx.exe" >nul
)
call "%INGEST_APP%\INICIAR_INGEST.bat"
exit /b %errorlevel%

:failed
echo A atualizacao nao foi concluida. Confira a mensagem acima.
pause
exit /b 1
