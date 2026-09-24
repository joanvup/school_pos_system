@echo off
title Compilar ACR122U_NFC.exe con PyInstaller
color 0E
cd /d "%~dp0backend"

echo ========================================================
echo   COMPILANDO EJECUTABLE STANDALONE PARA LECTOR ACR122U
echo ========================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno virtual en backend\venv.
    echo Cree el entorno e instale requirements.txt antes de compilar.
    pause
    exit /b 1
)

echo Compilando unicamente (--onefile), usando ACR122U_NFC.spec...
echo.
venv\Scripts\pyinstaller.exe --noconfirm --clean "ACR122U_NFC.spec"

echo.
if exist "dist\ACR122U_NFC.exe" (
    echo [EXITO] Ejecutable unico generado en backend\dist\ACR122U_NFC.exe
) else (
    echo [ERROR] La compilacion fallo.
)

pause
