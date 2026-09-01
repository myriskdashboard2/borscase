@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Borscase - validering
echo.
echo   Testar modellen mot verkligheten, ar for ar, med enbart information
echo   som var publicerad da. Plus en nollkontroll mot slumpmassiga poang.
echo.
echo   Vill du ha med rapportsignalerna ocksa, kor:
echo       python validering.py --rapporter
echo   (laddar ner cirka 800 arsredovisningar forsta gangen)
echo.
python validering.py %1 %2
echo.
pause
