@echo off
setlocal
title Tracker de Inmuebles Barranquilla - Servidor Local

chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ======================================================================
echo   [TRACKER] TRACKER DE APARTAMENTOS Y CASAS EN ARRIENDO - BARRANQUILLA NORTE
echo   Presupuesto Maximo: $2.500.000 COP (Canon + Administracion)
echo ======================================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] No se encontro Python en el PATH del sistema.
    echo Por favor asegurese de tener instalado Python 3.10 o superior.
    echo Descargue Python en: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [INFO] Iniciando servidor local y abriendo el dashboard en su navegador...
echo [INFO] Para detener el servidor, cierre esta ventana o presione Ctrl+C.
echo.

python run_dashboard.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AVISO] El servidor se detuvo con codigo de error %ERRORLEVEL%.
    pause
)
