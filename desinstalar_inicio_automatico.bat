@echo off
title Desinstalar Inicio Automatico - Lector NFC ACR122U
color 0C
cd /d "%~dp0"

set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SchoolPOS_NFC_Reader.lnk"

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo [EXITO] Se ha eliminado el inicio automatico del lector NFC.
) else (
    echo [INFO] El inicio automatico no estaba configurado.
)

echo.
pause
