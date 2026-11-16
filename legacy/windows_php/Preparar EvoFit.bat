@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    set "EVOFIT_PY=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Instale Python 3.10 ou superior antes de continuar.
        pause
        exit /b 1
    )
    set "EVOFIT_PY=python"
)
if not exist .env copy /y .env.example .env >nul
echo Antes de continuar, ligue MySQL no painel do XAMPP.
echo Esta preparacao preserva os registros existentes.
if exist evofit.sqlite3 (
    echo Banco SQLite antigo encontrado: sera feito backup e migracao para MySQL.
    %EVOFIT_PY% tools/manage.py migrate-sqlite --create-database
) else (
    %EVOFIT_PY% tools/manage.py init --create-database
)
if errorlevel 1 (
    echo.
    echo A preparacao nao terminou. Nao apague o banco antigo.
    echo Confira a mensagem acima e as instrucoes em LEIA PRIMEIRO.txt.
) else (
    echo.
    echo Banco preparado. Agora abra Iniciar EvoFit.bat.
)
pause
