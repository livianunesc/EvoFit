@echo off
setlocal
cd /d "%~dp0"
REM Versao avaliada: Python POO/Flask e MySQL. Execute MySQL no XAMPP primeiro.
python --version >nul 2>&1
if errorlevel 1 goto sempython
if not exist .venv\Scripts\python.exe python -m venv .venv
if errorlevel 1 goto erro
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto erro
.venv\Scripts\python.exe tools\preparar_academico.py --local
if errorlevel 1 goto erro
.venv\Scripts\python.exe app.py init-db --create-database
if errorlevel 1 goto erro
echo Pronto. Abra Iniciar EvoFit.bat. Dados existentes foram preservados.
pause
exit /b 0
:sempython
echo Instale Python 3.10 ou superior e habilite Add Python to PATH.
pause
exit /b 1
:erro
echo Preparacao interrompida. Verifique a mensagem, o MySQL e .env.academico.
echo Nao apague o banco nem os arquivos antigos.
pause
exit /b 1
