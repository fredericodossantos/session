@echo off
REM Executa o monitor a partir da pasta deste arquivo (usado pelo Agendador de Tarefas).
cd /d "%~dp0"
if errorlevel 1 exit /b 1
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m monitor_ac %*
) else (
    py -3 -m monitor_ac %*
)
exit /b %errorlevel%
