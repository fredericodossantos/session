@echo off
setlocal EnableExtensions
title Subir Monitor de Licitacoes - Goias

cd /d "%~dp0"
if errorlevel 1 exit /b 1
set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
set "CLOUDFLARED=%ROOT%tools\cloudflared.exe"
set "TOKEN_FILE=%ROOT%cloudflare-tunnel.token"
set "PUBLIC_URL=https://licitacoes-ac.98fred.dev/"
set "MONITOR_AC_MODO_ACESSO=publico"

if not exist "%PYTHON%" (
    echo [ERRO] Ambiente virtual nao encontrado: "%PYTHON%"
    echo Execute a preparacao do projeto antes de usar este arquivo.
    pause
    exit /b 1
)
if not exist "%CLOUDFLARED%" (
    echo [ERRO] cloudflared nao encontrado: "%CLOUDFLARED%"
    pause
    exit /b 1
)
powershell.exe -NoProfile -Command "$s = Get-AuthenticodeSignature -LiteralPath '%CLOUDFLARED%'; if ($s.Status -eq 'Valid' -and $s.SignerCertificate.Subject -like '*Cloudflare*') { exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo [ERRO] A assinatura digital de "%CLOUDFLARED%" nao pode ser confirmada como da Cloudflare.
    echo Baixe novamente o cloudflared.exe oficial em https://github.com/cloudflare/cloudflared/releases
    echo e substitua o arquivo em "tools\cloudflared.exe" antes de continuar.
    pause
    exit /b 1
)
if not exist "%TOKEN_FILE%" (
    echo [ERRO] Token do Cloudflare nao encontrado: "%TOKEN_FILE%"
    echo Gere um novo comando de conector no painel do Cloudflare e salve somente o token nesse arquivo.
    pause
    exit /b 1
)

"%PYTHON%" -c "from pathlib import Path; raise SystemExit(0 if Path('cloudflare-tunnel.token').read_text(encoding='utf-8').strip() else 1)"
if errorlevel 1 (
    echo [ERRO] O arquivo de token esta vazio ou nao pode ser lido.
    pause
    exit /b 1
)

echo Verificando a interface web local...
powershell.exe -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; $p=Get-NetTCPConnection -LocalPort 8765 -State Listen; if (-not $p) { exit 1 }; try { $h=Invoke-RestMethod 'http://127.0.0.1:8765/healthz' -TimeoutSec 3 } catch { exit 2 }; if ($h.access_mode -eq 'publico') { exit 0 } else { exit 2 }"
if errorlevel 2 (
    echo [ERRO] A porta 8765 esta ocupada por um servidor que nao confirmou o modo publico.
    echo Encerre essa instancia antes de disponibilizar o app pelo tunel.
    pause
    exit /b 1
)
if errorlevel 1 (
    echo Iniciando a interface web em modo publico...
    start "Monitor AC GO" /min "%PYTHON%" -m monitor_ac.web --modo-acesso publico --host 127.0.0.1 --port 8765 <nul
) else (
    echo A interface web ja esta em execucao no modo publico.
)
powershell.exe -NoProfile -Command "Start-Sleep -Seconds 2"
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; try { $h=Invoke-RestMethod 'http://127.0.0.1:8765/healthz' -TimeoutSec 3 } catch { exit 1 }; if ($h.access_mode -eq 'publico') { exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo [ERRO] O servidor web em modo publico nao respondeu. O tunel nao sera iniciado.
    pause
    exit /b 1
)

tasklist /FI "IMAGENAME eq cloudflared.exe" | find /I "cloudflared.exe" >nul
if errorlevel 1 (
    echo Iniciando o tunel Cloudflare...
    start "Cloudflare Tunnel - Monitor AC GO" /min "%CLOUDFLARED%" tunnel run --token-file "%TOKEN_FILE%" <nul
) else (
    echo O cloudflared ja esta em execucao; reutilizando o tunel.
)
powershell.exe -NoProfile -Command "Start-Sleep -Seconds 3"

echo.
echo Monitor disponivel em:
echo %PUBLIC_URL%
echo Mantenha esta maquina ligada para conservar o acesso publico.
start "" "%PUBLIC_URL%"

endlocal
exit /b 0
