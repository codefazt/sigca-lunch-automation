"""
Módulo para la limpieza automática y manual de archivos de logs y evidencias.
"""
import os
import glob
import time
import logging
from datetime import datetime
from src.config import BASE_DIR, load_status, save_status

logger = logging.getLogger("SiGCABot")

EVIDENCE_DIR = os.path.join(BASE_DIR, "evidence")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

def clean_old_logs_and_evidence(days=7):
    """
    Elimina archivos en evidence/ y logs/ que tengan una modificación mayor a 'days' días.
    """
    logger.info(f"Iniciando limpieza automática de archivos más antiguos de {days} días...")
    now = time.time()
    cutoff = now - (days * 86400)
    
    files_deleted = 0
    for directory in [EVIDENCE_DIR, LOGS_DIR]:
        if not os.path.exists(directory):
            continue
        
        for root, _, files in os.walk(directory):
            for file in files:
                if file == ".gitkeep":
                    continue
                    
                filepath = os.path.join(root, file)
                try:
                    if os.path.getmtime(filepath) < cutoff:
                        # Si es un log actual, el SO no dejará borrarlo, usamos try
                        os.remove(filepath)
                        files_deleted += 1
                except Exception as e:
                    logger.debug(f"No se pudo eliminar el archivo {filepath}: {e}")
                    
    logger.info(f"Limpieza automática completada. Archivos eliminados: {files_deleted}")
    
    status = load_status()
    status["last_cleanup_date"] = datetime.now().strftime("%Y-%m-%d")
    save_status(status)

def clean_all_logs_and_evidence():
    """
    Elimina todos los archivos en evidence/ y logs/ (excepto .gitkeep y el archivo bloqueado de logs actual).
    """
    logger.info("Iniciando limpieza MANUAL completa de evidencias y logs...")
    
    files_deleted = 0
    for directory in [EVIDENCE_DIR, LOGS_DIR]:
        if not os.path.exists(directory):
            continue
            
        for root, _, files in os.walk(directory):
            for file in files:
                if file == ".gitkeep":
                    continue
                    
                filepath = os.path.join(root, file)
                try:
                    os.remove(filepath)
                    files_deleted += 1
                except Exception as e:
                    logger.debug(f"No se pudo eliminar el archivo {filepath} (puede estar en uso): {e}")
                    
    logger.info(f"Limpieza manual completada. Archivos eliminados: {files_deleted}")
    
    status = load_status()
    status["last_cleanup_date"] = datetime.now().strftime("%Y-%m-%d")
    save_status(status)
    return files_deleted
