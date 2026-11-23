@echo off
chcp 65001 >nul
title Construir Cortei.exe
cd /d "%~dp0"

echo.
echo  ==== Construindo o Cortei.exe ====
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo  Python nao encontrado. Instale em https://www.python.org/downloads/
    echo  marcando "Add python.exe to PATH" e rode este arquivo de novo.
    echo.
    pause
    exit /b 1
)

echo  [1/3] Instalando dependencias e o PyInstaller...
%PY% -m pip install --upgrade pip >nul 2>nul
%PY% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo.
    echo  Falha ao instalar as dependencias. Veja a mensagem acima.
    pause
    exit /b 1
)

echo.
echo  [2/3] Empacotando (leva alguns minutos)...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name Cortei ^
    --icon cortei.ico ^
    --add-data "cortei.ico;." ^
    --collect-all customtkinter ^
    --collect-all imageio_ffmpeg ^
    cortei.py
if errorlevel 1 (
    echo.
    echo  O empacotamento falhou. Veja a mensagem acima.
    pause
    exit /b 1
)

if not exist "dist\Cortei.exe" (
    echo.
    echo  Nao encontrei dist\Cortei.exe. Algo deu errado no empacotamento.
    pause
    exit /b 1
)

echo.
echo  [3/3] Pronto!
echo.
echo  O programa esta em:  %~dp0dist\Cortei.exe
echo  Voce pode copiar so esse arquivo para qualquer lugar ou enviar para amigos.
echo.
explorer "%~dp0dist"
pause
