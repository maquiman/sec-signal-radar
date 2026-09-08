@echo off
setlocal
title SEC Signal Radar

cd /d "%~dp0"

echo ========================================
echo SEC Signal Radar
echo ========================================
echo.
echo Carpeta del proyecto:
echo %CD%
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual .venv...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo.
        echo No se pudo crear el entorno con py -3. Intentando con python...
        python -m venv .venv
        if errorlevel 1 (
            echo.
            echo ERROR: No se encontro Python o fallo la creacion del entorno virtual.
            echo Instala Python y vuelve a hacer doble click en este archivo.
            echo.
            pause
            exit /b 1
        )
    )
    echo.
)

".venv\Scripts\python.exe" -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: No se pudieron instalar las dependencias.
        echo Revisa tu conexion a internet y vuelve a intentarlo.
        echo.
        pause
        exit /b 1
    )
    echo.
)

echo Abriendo dashboard...
echo Manten esta ventana abierta mientras uses la aplicacion.
echo Para cerrar el servidor, presiona Ctrl+C en esta ventana.
echo.

".venv\Scripts\python.exe" -m streamlit run "src\dashboard\app.py"

echo.
echo El dashboard se cerro.
pause
