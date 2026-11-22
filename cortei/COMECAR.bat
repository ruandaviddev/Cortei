@echo off
chcp 65001 >nul
title Cortei
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo.
    echo  O Python nao foi encontrado neste computador.
    echo.
    echo  1. Baixe em: https://www.python.org/downloads/
    echo  2. Na instalacao, MARQUE a opcao "Add python.exe to PATH"
    echo  3. Depois de instalar, de dois cliques neste arquivo de novo.
    echo.
    pause
    exit /b 1
)

%PY% -c "import tkinter, customtkinter, numpy, imageio_ffmpeg" >nul 2>nul
if errorlevel 1 (
    echo  Instalando os componentes necessarios... pode levar um minuto.
    %PY% -m pip install -r requirements.txt
    %PY% -c "import tkinter, customtkinter, numpy, imageio_ffmpeg" >nul 2>nul
    if errorlevel 1 (
        echo.
        echo  Nao consegui preparar tudo. Veja a mensagem acima.
        echo  Se falou de "tkinter", reinstale o Python marcando "tcl/tk and IDLE".
        echo.
        pause
        exit /b 1
    )
)

where pyw >nul 2>nul && (start "" pyw -3 "%~dp0cortei.py" & exit /b 0)
where pythonw >nul 2>nul && (start "" pythonw "%~dp0cortei.py" & exit /b 0)
%PY% "%~dp0cortei.py"
