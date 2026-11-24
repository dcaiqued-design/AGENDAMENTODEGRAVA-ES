@echo off
setlocal
title Ingest Control - Gerador RTMP de teste
cd /d "%~dp0.."
if defined INGEST_FFMPEG (
  set "FFMPEG=%INGEST_FFMPEG%"
) else (
  set "FFMPEG=ffmpeg"
)
echo.
echo Gerando barras de teste 640x360 a 25 fps + tom de 440 Hz.
echo Publicando apenas no computador local.
echo Pressione Q nesta janela para encerrar o sinal.
echo.
"%FFMPEG%" -hide_banner -re -f lavfi -i "testsrc2=size=640x360:rate=25" -re -f lavfi -i "sine=frequency=440:sample_rate=48000" -map 0:v:0 -map 1:a:0 -c:v libx264 -preset ultrafast -tune zerolatency -g 50 -pix_fmt yuv420p -b:v 1100k -c:a aac -ar 48000 -b:a 96k -f flv "rtmp://127.0.0.1:1935/live/test"
if errorlevel 1 (
  echo.
  echo Nao foi possivel publicar o sinal.
  echo Confira se o MediaMTX esta aberto e o FFmpeg tem encoder libx264.
)
pause
