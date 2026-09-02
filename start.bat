@echo off
chcp 65001 > nul
title Vagas RS - Pelotas e Rio Grande

echo =======================================================
echo    🚀 SISTEMA DE MONITORAMENTO DE VAGAS RS
echo    Pelotas & Rio Grande - Elétrica, TI Jr & Projetos
echo =======================================================
echo.

if exist ".venv\Scripts\python.exe" (
    echo [INFO] Iniciando com ambiente virtual Python...
    start http://localhost:8000
    .venv\Scripts\python.exe server.py
) else (
    echo [INFO] Iniciando com Python do sistema...
    start http://localhost:8000
    python server.py
)

pause
