@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Borscase - installation
echo.
echo   ============================================================
echo     BORSCASE - installation
echo   ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo   Python hittades inte pa den har datorn.
  echo.
  echo   Ladda ner Python fran https://www.python.org/downloads/
  echo   VIKTIGT vid installationen: kryssa i rutan
  echo       "Add Python to PATH"
  echo   langst ner i forsta fonstret. Utan den kryssen hittar inte
  echo   Windows Python, och den har filen sager samma sak igen.
  echo.
  echo   Kor sedan INSTALLERA.bat pa nytt.
  echo.
  pause
  exit /b 1
)

for /f "tokens=*" %%v in ('python --version') do echo   Hittade %%v
echo.
echo   Installerar de fem paket som behovs...
echo   (yfinance, pandas, numpy, flask, pypdf)
echo.
python -m pip install --quiet --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo   Nagot gick fel i installationen. Vanligaste orsaken ar att
  echo   datorn saknar internet just nu. Prova igen.
  echo.
  pause
  exit /b 1
)

echo.
echo   ============================================================
echo     Klart. Gor sa har nu:
echo.
echo       1. SKANNA.bat        hamtar all data (tar 15-30 minuter
echo                            forsta gangen, sedan under en minut)
echo       2. STARTA_APP.bat    oppnar appen i webblasaren
echo       3. STOPPA_APP.bat    nar du ar klar
echo.
echo     Las garna LAS_MIG.txt forst - sarskilt stycket om vad
echo     appens egen validering faktiskt visade.
echo   ============================================================
echo.
pause
