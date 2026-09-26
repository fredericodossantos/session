@echo off
REM Executa o monitor a partir da pasta deste arquivo (usado pelo Agendador de Tarefas).
cd /d "%~dp0"
if errorlevel 1 exit /b 1
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m monitor_ac %*
) else (
    where py >nul 2>nul
    if errorlevel 1 (
        echo [ERRO] Nao foi encontrado o Python ^(comando 'py'^) neste computador.
        echo Instale o Python 3.11 ou mais novo em https://python.org e marque
        echo "Add python.exe to PATH" durante a instalacao.
        echo Depois crie o ambiente virtual deste projeto, na pasta deste arquivo
        echo ^(veja o README.md^):
        echo   py -3 -m venv .venv
        echo   .venv\Scripts\python -m pip install -r requirements.txt
        exit /b 1
    )
    py -3 -c "import requests, yaml, openpyxl" >nul 2>nul
    if errorlevel 1 (
        echo [ERRO] Ambiente virtual ^(.venv^) nao encontrado, e o Python do sistema
        echo nao tem as dependencias deste projeto instaladas.
        echo Crie o ambiente virtual na pasta deste arquivo e rode novamente
        echo ^(veja o README.md^):
        echo   py -3 -m venv .venv
        echo   .venv\Scripts\python -m pip install -r requirements.txt
        exit /b 1
    )
    py -3 -m monitor_ac %*
)
exit /b %errorlevel%
