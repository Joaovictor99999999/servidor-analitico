@echo off
title Servidor de Relatorios - OLS
echo ===================================================
echo    INICIANDO A INTERFACE DO SERVIDOR OLS
echo ===================================================
echo.
echo Iniciando o motor offline e carregando a interface...
echo Por favor, nao feche esta janela preta.
echo.

:: O comando abaixo chama o Python portatil e roda a nova interface
.\motor_offline\python.exe -m streamlit run codigo_fonte\interface_servidor.py --server.port 8501 --server.address 0.0.0.0

pause