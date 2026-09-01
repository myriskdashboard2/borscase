@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Borscase - skanning
echo.
echo   ============================================================
echo     BORSCASE - skannar 217 bolag
echo   ============================================================
echo.
echo   Hamtar bokslut, kurser, arsredovisningar och rapportdatum.
echo.
echo   FORSTA GANGEN tar det 15-30 minuter. Det ar inte trasigt -
echo   det laddas ner cirka 900 arsredovisningar och 20 ars bokslut
echo   per bolag. Allt sparas i mappen cache\, sa nasta korning tar
echo   under en minut.
echo.
echo   Lat fonstret vara oppet. Raknaren langst ner visar hur langt
echo   det har gatt.
echo.
python skanning.py %1 %2
echo.
echo   Klart. Starta appen med STARTA_APP.bat.
echo.
pause
