@echo off
setlocal
title Ingest Control - Servidor RTMP local
cd /d "%~dp0.."
if not exist "tools\mediamtx\mediamtx.exe" (
  echo ERRO: mediamtx.exe nao encontrado em tools\mediamtx\
  echo Baixe o pacote Windows AMD64 em https://github.com/bluenviron/mediamtx/releases
  echo Extraia mediamtx.exe e mediamtx.yml na pasta tools\mediamtx\
  echo Nao envie os executaveis ao GitHub.
  pause
  exit /b 1
)
REM Para o teste, restringe o RTMP ao proprio computador e desativa outros listeners.
set "MTX_RTMPADDRESS=127.0.0.1:1935"
set "MTX_RTSP=false"
set "MTX_HLS=false"
set "MTX_WEBRTC=false"
set "MTX_SRT=false"
set "MTX_API=false"
set "MTX_METRICS=false"
set "MTX_PPROF=false"
set "MTX_PLAYBACK=false"
echo.
echo Servidor RTMP de teste - apenas localhost
echo URL: rtmp://127.0.0.1:1935/live/test
echo Mantenha esta janela aberta durante o teste.
echo.
pushd "tools\mediamtx"
mediamtx.exe
set "STATUS=%errorlevel%"
popd
echo Servidor RTMP encerrado.
pause
exit /b %STATUS%
