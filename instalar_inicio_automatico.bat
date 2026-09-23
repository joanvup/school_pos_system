@echo off
title Instalar Inicio Automatico - Lector NFC ACR122U
color 0B
cd /d "%~dp0"

echo ========================================================
echo   CONFIGURAR INICIO AUTOMATICO CON WINDOWS
echo ========================================================
echo.

set "EXE_PATH=%~dp0backend\dist\ACR122U_NFC\ACR122U_NFC.exe"
set "TARGET_VBS=%~dp0iniciar_lector_silencioso.vbs"
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SchoolPOS_NFC_Reader.lnk"

if exist "%EXE_PATH%" (
    echo Usando ejecutable compilado ACR122U_NFC.exe...
    powershell -Command "$s = (New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%EXE_PATH%'; $s.WorkingDirectory = '%~dp0backend\dist\ACR122U_NFC'; $s.Description = 'Lector NFC ACR122U para School POS'; $s.Save()"
) else (
    echo Usando script silencioso VBS...
    powershell -Command "$s = (New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%TARGET_VBS%\"'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Lector NFC ACR122U para School POS'; $s.Save()"
)

if exist "%SHORTCUT_PATH%" (
    echo.
    echo [EXITO] Acceso directo creado en la carpeta de Inicio de Windows.
    echo El lector NFC se iniciara automaticamente en segundo plano cada vez
    echo que el computador se encienda.
    echo.
) else (
    echo.
    echo [ERROR] No se pudo crear el acceso directo de inicio automatico.
    echo.
)

pause
