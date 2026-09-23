@echo off
title Compilar ACR122U_NFC.exe con PyInstaller
color 0E
cd /d "%~dp0backend"

echo ========================================================
echo   COMPILANDO EJECUTABLE STANDALONE PARA LECTOR ACR122U
echo ========================================================
echo.

venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed --name "ACR122U_NFC" --hidden-import="pystray._win32" --hidden-import="PIL" --hidden-import="smartcard" --hidden-import="smartcard.System" --hidden-import="smartcard.util" acr122u_bridge.py

echo.
if exist "dist\ACR122U_NFC\ACR122U_NFC.exe" (
    echo [EXITO] Ejecutable generado en backend\dist\ACR122U_NFC\ACR122U_NFC.exe
) else (
    echo [ERROR] La compilacion fallo.
)

pause
