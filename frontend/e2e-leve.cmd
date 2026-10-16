@echo off
rem Roda o Playwright com prioridade baixa: os navegadores herdam a prioridade e a máquina não trava.
start "" /low /b /wait npx playwright test %*
