@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    set "EVOFIT_PY=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo O Python nao foi encontrado. Instale Python 3.10 ou superior em python.org.
        echo Depois abra este arquivo novamente.
        pause
        exit /b 1
    )
    set "EVOFIT_PY=python"
)
echo Iniciando o EvoFit. Mantenha esta janela aberta enquanto usa o aplicativo.
echo No navegador, abra: http://localhost:4173
start "" /b powershell -NoProfile -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:4173'"
%EVOFIT_PY% server.py
if errorlevel 1 (
    echo.
    echo O EvoFit nao iniciou. Confira a mensagem acima.
)
pause
