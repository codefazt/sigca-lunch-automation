@echo off
:: =============================================================================
:: SiGCABot — Script de Compilación Automatizada
:: =============================================================================
:: Este script construye el ejecutable portable de Windows (.exe) listo para
:: distribución. Empaqueta todos los recursos necesarios y crea una carpeta
:: limpia de release.
::
:: Requisitos:
::   - Entorno virtual 'venv' con todas las dependencias instaladas
::   - PyInstaller instalado (incluido en requirements.txt)
::   - Playwright Chromium instalado en el sistema del usuario final
::
:: Uso:
::   build.bat
:: =============================================================================

:: Procesar argumentos
set "HELP_FLAG="
set "PACKAGE_FLAG="
set "NO_PAUSE="

:parse_args
if "%~1"=="" goto after_args
if "%~1"=="-h" set HELP_FLAG=1
if "%~1"=="--help" set HELP_FLAG=1
if "%~1"=="--package" set PACKAGE_FLAG=1
set NO_PAUSE=1
shift
goto parse_args

:after_args
if defined HELP_FLAG (
    echo ===================================================
    echo    SiGCABot - Compilacion Automatizada
    echo ===================================================
    echo.
    echo Uso: build.bat [opciones]
    echo.
    echo Opciones:
    echo   -h, --help      Muestra esta ayuda y la documentacion del empaquetado.
    echo   --package       Compila la aplicacion y comprime la salida en un archivo .zip listo para distribuir.
    echo.
    echo Documentacion de distribucion:
    echo   El script creara un paquete de distribucion en dist\SiGCABot_Release\
    echo   que incluye todos los archivos necesarios para que la aplicacion funcione
    echo   de forma portable en cualquier otra maquina Windows de 64 bits.
    echo.
    echo   Solo tendras que descomprimir el ZIP, renombrar .env.template a .env,
    echo   ingresar las credenciales de SiGCA y el bot/chat ID de Telegram,
    echo   y correr SiGCABot.exe.
    exit /b 0
)

echo.
echo ===================================================
echo    SiGCABot - Compilacion Automatizada
echo    Fecha: %date% %time%
echo ===================================================
echo.

:: Cambiar al directorio donde reside este script
cd /d "%~dp0"

:: Verificar entorno virtual
if not exist "venv" (
    echo [ERROR] No se encontro el entorno virtual 'venv'.
    echo         Ejecuta primero: python -m venv venv
    echo         Luego: pip install -r requirements.txt
    if not defined NO_PAUSE (
        pause
    )
    exit /b 1
)

:: Activar entorno virtual
echo [1/5] Activando entorno virtual...
call venv\Scripts\activate

:: Verificar PyInstaller
where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [WARN] PyInstaller no encontrado. Instalando...
    pip install pyinstaller
)

:: Limpiar build anterior
echo [2/5] Limpiando compilaciones anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist\SiGCABot_Release" rmdir /s /q "dist\SiGCABot_Release"

:: Compilar con PyInstaller
echo [3/5] Compilando el ejecutable con PyInstaller...
echo         Esto puede tardar varios minutos...
echo.
pyinstaller SiGCABot.spec --noconfirm

if errorlevel 1 (
    echo.
    echo [ERROR] La compilacion fallo. Revisa los errores de PyInstaller arriba.
    pause
    exit /b 1
)

:: Crear carpeta de release limpia
echo [4/5] Creando paquete de distribucion en dist\SiGCABot_Release\...
mkdir "dist\SiGCABot_Release" 2>nul

:: Copiar ejecutable
copy /y "dist\SiGCABot.exe" "dist\SiGCABot_Release\SiGCABot.exe"

:: Copiar archivos de soporte
copy /y ".env.template" "dist\SiGCABot_Release\.env.template"
copy /y "run_job.bat" "dist\SiGCABot_Release\run_job.bat"
copy /y "README.md" "dist\SiGCABot_Release\README.md"
copy /y "WINDOWS_SCHEDULER.md" "dist\SiGCABot_Release\WINDOWS_SCHEDULER.md"

:: Copiar carpeta de imágenes de manual
xcopy /e /i /y "images_info" "dist\SiGCABot_Release\images_info"

:: Crear carpetas necesarias
mkdir "dist\SiGCABot_Release\logs" 2>nul
mkdir "dist\SiGCABot_Release\evidence" 2>nul


:: Crear config.json por defecto
echo {"start_hour": 15, "start_minute": 30, "end_hour": 10, "end_minute": 0, "timeout_ms": 30000, "headless": true, "retries": 3, "retry_delay_sec": 300, "prefer_menu": "saludable"} > "dist\SiGCABot_Release\config.json"

echo.
echo [5/5] Compilacion completada exitosamente!
echo.
echo ===================================================
echo    Paquete de distribucion listo en:
echo    dist\SiGCABot_Release\
echo.
echo    Contenido:
echo      - SiGCABot.exe         (Ejecutable principal)
echo      - .env.template        (Plantilla de credenciales)
echo      - config.json          (Configuracion por defecto)
echo      - run_job.bat          (Script para Task Scheduler)
echo      - README.md            (Documentacion)
echo      - WINDOWS_SCHEDULER.md (Guia de programacion)
echo      - logs\                (Directorio de logs)
echo      - evidence\            (Directorio de capturas)
echo ===================================================
echo.

if defined PACKAGE_FLAG (
    echo [INFO] Creando archivo comprimido ZIP para distribucion...
    if exist "dist\SiGCABot_Release.zip" del /f /q "dist\SiGCABot_Release.zip"
    
    echo [INFO] Esperando 5 segundos para que Windows libere el ejecutable...
    timeout /t 5 /nobreak >nul
    
    powershell -NoProfile -Command "Compress-Archive -Path dist\SiGCABot_Release\* -DestinationPath dist\SiGCABot_Release.zip -Force"
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el archivo ZIP.
    ) else (
        echo.
        echo ===================================================
        echo    [EXITO] Paquete comprimido creado exitosamente en:
        echo    dist\SiGCABot_Release.zip
        echo ===================================================
        echo.
    )
)

if not defined NO_PAUSE (
    pause
)
