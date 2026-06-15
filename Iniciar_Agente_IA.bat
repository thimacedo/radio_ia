@echo off
title Agente de IA - Rádio TJRN
echo ===================================================
echo   Iniciando Execucao Unica do Agente de IA...
echo ===================================================
python "%~dp0modules\agente\agente_ia.py" --once
echo.
echo ===================================================
echo   Execucao concluida! Pressione qualquer tecla...
echo ===================================================
pause
