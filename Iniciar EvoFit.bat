@echo off
setlocal
cd /d "%~dp0"
REM Mantenha o MySQL e esta janela abertos. O navegador usa a API Flask.
if not exist .venv\Scripts\python.exe (
 echo Execute Preparar EvoFit.bat primeiro.
 pause
 exit /b 1
)
start "" "http://127.0.0.1:4173"
.venv\Scripts\python.exe server.py
if errorlevel 1 (
 echo Verifique o MySQL, a porta 4173 e a configuracao .env.academico.
 pause
 exit /b 1
)
