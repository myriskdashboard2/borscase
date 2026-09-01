@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Borscase
echo.
echo   Borscase startar pa http://127.0.0.1:8810
echo   Webblasaren oppnas av sig sjalv. Stang med STOPPA_APP.bat.
echo.
python app.py
pause
