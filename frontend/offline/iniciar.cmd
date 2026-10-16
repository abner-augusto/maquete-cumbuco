@echo off
rem Abre a maquete sem internet: sobe o servidor local e o navegador. Feche a janela para parar.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0servidor.ps1" %*
