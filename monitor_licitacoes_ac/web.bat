@echo off
REM Abre a interface web local do monitor.
cd /d "%~dp0"
if errorlevel 1 exit /b 1
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m monitor_ac.web --open %*
) else (
    py -3 -m monitor_ac.web --open %*
)
exit /b %errorlevel%
