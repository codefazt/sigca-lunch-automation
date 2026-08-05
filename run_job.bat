@echo off
:: Desactivar salida de eco para que sea más limpio
echo ===================================================
echo [SIGCA LUNCH AUTOMATION] Iniciando ejecucion del Job
echo Fecha y hora: %date% %time%
echo ===================================================

:: Cambiar al directorio donde reside el script
cd /d "%~dp0"

:: Verificar si el entorno virtual existe
if not exist "venv" (
    echo [ERROR] No se detecto el entorno virtual 'venv'. Creando entorno...
    python -m venv venv
    call venv\Scripts\activate
    echo [INFO] Instalando dependencias desde requirements.txt...
    pip install -r requirements.txt
    echo [INFO] Instalando navegadores de Playwright...
    playwright install chromium
) else (
    call venv\Scripts\activate
)

:: Ejecutar el entrypoint CLI seguro. Este flujo consulta y actualiza status.json.
:: Nota: pasamos los argumentos recibidos al batch script (ej. --dry-run o --force-time)
if /I "%~1"=="--cancel-order" (
    python app_gui.py --cancel-order %~2 %~3 %~4 %~5 %~6 %~7 %~8 %~9
) else (
    python app_gui.py --run-job %*
)

echo ===================================================
echo [SIGCA LUNCH AUTOMATION] Ejecucion finalizada con codigo: %errorlevel%
echo ===================================================
exit /b %errorlevel%
