@echo off
setlocal
cd /d "%~dp0"
REM Abre o index.html somente depois de o servidor e o banco responderem.
if exist .venv\Scripts\python.exe goto local

REM Instalacoes Docker nao precisam do ambiente virtual local.
python --version >nul 2>&1
if errorlevel 1 goto sempython
docker info >nul 2>&1
if errorlevel 1 goto preparar
python tools\docker_academico.py iniciar --abrir
if errorlevel 1 goto erro
exit /b 0

:local
REM MySQL do XAMPP deve estar ligado. Mantenha esta janela aberta.
.venv\Scripts\python.exe server.py --abrir
if errorlevel 1 goto erro
exit /b 0

:preparar
echo Execute Preparar EvoFit.bat com o MySQL ligado, ou abra o Docker Desktop.
pause
exit /b 1

:sempython
echo Instale Python 3.10 ou superior e habilite Add Python to PATH.
pause
exit /b 1

:erro
echo Nao foi possivel iniciar. Confira a mensagem, o MySQL e a porta 4173.
pause
exit /b 1
