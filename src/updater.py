"""
Módulo de actualización automática para SiGCABot.
Permite consultar la API de GitHub, descargar el ZIP de la release en segundo plano
y ejecutar un script batch temporal para aplicar los cambios sin bloquear el proceso principal.
"""

import os
import sys
import json
import zipfile
import logging
import urllib.request
import subprocess
from src.config import BASE_DIR, APP_VERSION

logger = logging.getLogger("SiGCABot")

GITHUB_REPO = "codefazt/sigca-lunch-automation"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def parse_version(v_str):
    """Parsea una cadena de versión semántica (ej. 'v2.2.0' o '2.3') en una tupla de enteros."""
    if not v_str:
        return (0, 0, 0)
    v_str = v_str.lower().lstrip('v').strip()
    parts = []
    for p in v_str.split('.'):
        num = ""
        for char in p:
            if char.isdigit():
                num += char
            else:
                break
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])

def check_for_update():
    """
    Comprueba si existe una versión más reciente en GitHub Releases.
    
    Returns:
        tuple: (has_update, remote_version, download_url, release_notes)
    """
    try:
        req = urllib.request.Request(
            RELEASES_API,
            headers={"User-Agent": "SiGCABot-Updater"}
        )
        
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status != 200:
                logger.warning(f"La API de GitHub retornó código {response.status} al verificar actualización.")
                return False, None, None, None
                
            data = json.loads(response.read().decode("utf-8"))
            remote_tag = data.get("tag_name", "")
            if not remote_tag:
                return False, None, None, None
                
            current_v = parse_version(APP_VERSION)
            remote_v = parse_version(remote_tag)
            
            if remote_v > current_v:
                # Buscar el asset ZIP de release
                assets = data.get("assets", [])
                download_url = None
                
                # Intentar encontrar un ZIP en los assets
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if name.endswith(".zip"):
                        download_url = asset.get("browser_download_url")
                        break
                        
                if download_url:
                    release_notes = data.get("body", "No hay notas disponibles para esta versión.")
                    return True, remote_tag, download_url, release_notes
                else:
                    logger.warning("Nueva release encontrada pero no se detectó un archivo ZIP de distribución.")
                    
    except urllib.error.HTTPError as he:
        if he.code == 404:
            logger.info("No se encontraron releases publicadas en el repositorio de GitHub.")
        else:
            logger.warning(f"Error HTTP al consultar API de GitHub: {he}")
    except Exception as e:
        logger.warning(f"Error de red o conexión al verificar actualizaciones: {e}")
        
    return False, None, None, None

def download_and_prepare_update(download_url, progress_callback=None):
    """
    Descarga el ZIP de actualización y lo extrae en la carpeta temporal updates/extracted/.
    
    Args:
        download_url (str): URL de descarga del ZIP.
        progress_callback (callable): Callback que recibe el porcentaje (0 a 100).
    """
    update_dir = os.path.join(BASE_DIR, "updates")
    extracted_dir = os.path.join(update_dir, "extracted")
    
    # Crear carpetas si no existen, o limpiarlas si ya existían de un intento previo
    if os.path.exists(update_dir):
        import shutil
        try:
            shutil.rmtree(update_dir)
        except Exception:
            pass
            
    os.makedirs(extracted_dir, exist_ok=True)
    zip_path = os.path.join(update_dir, "update.zip")
    
    # Comprobar si es un archivo local de prueba (mock de prueba local)
    if not download_url.startswith("http://") and not download_url.startswith("https://"):
        if os.path.exists(download_url):
            logger.info(f"Modo Test Local: Copiando ZIP de prueba desde {download_url}...")
            import shutil
            import time
            if progress_callback:
                progress_callback(25)
                time.sleep(0.3)
                progress_callback(75)
                time.sleep(0.3)
                progress_callback(100)
            shutil.copy(download_url, zip_path)
        else:
            raise FileNotFoundError(f"No se encontró el ZIP local de prueba en {download_url}")
    else:
        logger.info(f"Iniciando descarga de actualización desde {download_url}...")
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "SiGCABot-Updater"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = int(response.info().get('Content-Length', 0))
            bytes_read = 0
            chunk_size = 16384
            with open(zip_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_read += len(chunk)
                    if progress_callback and total_size > 0:
                        percent = int((bytes_read / total_size) * 100)
                        progress_callback(percent)
                        
    logger.info("Descarga/copia completada. Extrayendo archivos...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extracted_dir)
    logger.info(f"Archivos extraídos en {extracted_dir}.")

def launch_updater_script():
    """
    Escribe el script batch temporal y lo ejecuta de forma desvinculada
    para aplicar la actualización y reiniciar la aplicación.
    """
    update_dir = os.path.join(BASE_DIR, "updates")
    extracted_dir = os.path.join(update_dir, "extracted")
    bat_path = os.path.join(update_dir, "updater.bat")
    
    # Determinar el directorio de origen real (manejando subcarpetas si el ZIP es de GitHub)
    source_dir = extracted_dir
    try:
        items = os.listdir(extracted_dir)
        if len(items) == 1 and os.path.isdir(os.path.join(extracted_dir, items[0])):
            source_dir = os.path.join(extracted_dir, items[0])
    except Exception as e:
        logger.warning(f"Error al analizar el directorio extraído: {e}")
        
    is_frozen = getattr(sys, 'frozen', False)
    
    # Determinar la carpeta de instalación física real de la app
    if is_frozen:
        install_dir = os.path.dirname(sys.executable)
        exe_path = os.path.join(install_dir, "SiGCABot.exe")
        restart_cmd = f'start "" "{exe_path}"'
    else:
        install_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        restart_cmd = 'start "" "venv\\Scripts\\python.exe" "app_gui.py"'
        
    bat_content = f"""@echo off
chcp 65001 > nul
title Actualizando SiGCABot...
echo ===============================================
echo   Instalando actualizacion de SiGCABot...
echo   Por favor, espere un momento.
echo ===============================================
echo.
echo [1/3] Esperando que se liberen los archivos...
timeout /t 3 /nobreak > nul
taskkill /f /im SiGCABot.exe > nul 2>&1

echo [2/3] Copiando nuevos archivos...
:: Copiar desde el directorio extraido.
:: Excluye .env, config.json y status.json para mantener credenciales y configuracion del usuario.
robocopy "{source_dir}" "{install_dir}" /E /NJH /NJS /NDL /NC /NS /XF ".env" "config.json" "status.json"

echo [3/3] Reiniciando la aplicacion...
{restart_cmd}

echo.
echo Limpiando archivos temporales...
:: Ejecuta un proceso en segundo plano para borrar la carpeta updates una vez que este script termine
start /b cmd /c "timeout /t 2 /nobreak > nul && rd /s /q \\"{update_dir}\\""

:: Auto-eliminarse
del "%~f0"
"""
    
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content.replace('\n', '\r\n'))
        
    logger.info(f"Script de actualización generado. Origen: {source_dir} -> Destino: {install_dir}")
    logger.info("Lanzando actualizador...")
    
    # Ejecutar en Windows de forma asíncrona y separada
    subprocess.Popen(
        f'cmd.exe /c "{bat_path}"',
        shell=True,
        cwd=install_dir,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
    )
