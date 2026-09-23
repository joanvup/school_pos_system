@echo off
title School POS - Servicio Lector NFC ACR122U
color 0A
cd /d "%~dp0backend"

echo ========================================================
echo   SCHOOL POS - PUENTE LECTOR NFC ACR122U
echo ========================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno virtual en backend\venv.
    echo Creando entorno e instalando dependencias...
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt
)

echo Iniciando servicio del lector NFC...
echo (Se mostrara un icono en la bandeja del sistema junto al reloj)
echo.
venv\Scripts\python.exe acr122u_bridge.py --mode wedge
pause
