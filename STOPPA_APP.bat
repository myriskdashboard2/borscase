@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist app.pid (
  for /f %%p in (app.pid) do taskkill /PID %%p /F >nul 2>&1
  del app.pid >nul 2>&1
  echo   Borscase stoppad.
) else (
  echo   Ingen app.pid hittades - appen kanske inte kor.
)
timeout /t 2 >nul
