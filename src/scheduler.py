"""
Planificador diario e integración con el Programador de Tareas de Windows.

Contiene:
- Planificador en background que ejecuta la automatización en el rango horario.
- Funciones para registrar/eliminar/verificar tareas programadas en Windows
  con elevación dinámica de privilegios (UAC).
"""

import os
import sys
import time
import logging
import subprocess
import base64
from datetime import datetime

from src.config import BASE_DIR, load_status, save_status, load_config
from src.bot_engine import LunchBot
from src import state

logger = logging.getLogger("SiGCABot")

# Nombre de la tarea en el Programador de Tareas de Windows
TASK_NAME = "SiGCA Auto Lunch Order"


# ---------------------------------------------------------------------------
# Ejecución del Job de Automatización
# ---------------------------------------------------------------------------

def run_lunch_automation_job(dry_run=False, gui_update_callback=None):
    """
    Ejecuta el job de automatización del almuerzo y actualiza status.json.

    Args:
        dry_run: Si es True, no confirma el pedido final.
        gui_update_callback: Función opcional para refrescar el badge de la GUI.
    """
    try:
        bot = LunchBot()
        exit_code, msg, evidence = bot.run_automation(dry_run=dry_run)

        status_info = load_status()
        status_info["last_run_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if exit_code == 0:
            status_info["last_run_status"] = "success"
            if not dry_run:
                status_info["last_successful_run"] = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"ÉXITO: {msg}")
        else:
            status_info["last_run_status"] = f"error (código {exit_code})"
            logger.error(f"FALLO: {msg}")
            # Si error de login/credenciales (código 1), pausar para evitar bloqueo de cuenta
            if exit_code == 1:
                status_info["is_active"] = False
                logger.warning("Planificador desactivado automáticamente debido a error de credenciales/login.")

        save_status(status_info)
        if gui_update_callback:
            gui_update_callback()

    except Exception as e:
        logger.error(f"Error crítico ejecutando automatización de almuerzo: {e}")
        status_info = load_status()
        status_info["last_run_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_info["last_run_status"] = "error (excepción)"
        save_status(status_info)
        if gui_update_callback:
            gui_update_callback()


# ---------------------------------------------------------------------------
# Planificador en Background
# ---------------------------------------------------------------------------

def start_scheduler(gui_update_callback=None):
    """
    Loop del planificador que corre en un hilo en segundo plano.
    Comprueba cada 60 segundos si debe ejecutarse la automatización.

    Args:
        gui_update_callback: Función opcional para refrescar la GUI.
    """
    logger.info("Hilo Planificador iniciado. Buscando ventana horaria configurada.")
    while not state.stop_threads:
        try:
            status_info = load_status()
            
            # --- Limpieza automática semanal ---
            last_cleanup_str = status_info.get("last_cleanup_date", "")
            today_date = datetime.now()
            needs_cleanup = False
            
            if not last_cleanup_str:
                needs_cleanup = True
            else:
                try:
                    last_cleanup = datetime.strptime(last_cleanup_str, "%Y-%m-%d")
                    if (today_date - last_cleanup).days >= 7:
                        needs_cleanup = True
                except Exception:
                    needs_cleanup = True
                    
            if needs_cleanup:
                try:
                    from src.cleanup import clean_old_logs_and_evidence
                    clean_old_logs_and_evidence(days=7)
                    # Recargar status ya que cleanup.py lo modificó
                    status_info = load_status()
                except Exception as e:
                    logger.error(f"Error durante la limpieza automática semanal: {e}")
            # -----------------------------------

            if status_info.get("is_active", True) and not status_info.get("is_cancelled_today", False):
                # Comprobar si ya se ejecutó con éxito hoy
                today_str = datetime.now().strftime("%Y-%m-%d")
                if status_info.get("last_successful_run") != today_str:

                    config = load_config()
                    retry_delay = config.get("retry_delay_sec", 300)

                    # Comprobar cuándo fue la última ejecución (para delay de reintentos)
                    last_run_str = status_info.get("last_run_timestamp", "")
                    should_run = True

                    if last_run_str and last_run_str != "Nunca":
                        try:
                            last_run_time = datetime.strptime(last_run_str, "%Y-%m-%d %H:%M:%S")
                            elapsed = (datetime.now() - last_run_time).total_seconds()
                            if elapsed < retry_delay:
                                should_run = False
                        except Exception:
                            pass

                    if should_run:
                        # Verificar ventana horaria directamente sin crear LunchBot
                        from datetime import time as dt_time
                        current_t = datetime.now().time()
                        start_t = dt_time(config.get("start_hour", 15), config.get("start_minute", 30))
                        end_t = dt_time(config.get("end_hour", 10), config.get("end_minute", 0))

                        if start_t <= end_t:
                            time_valid = start_t <= current_t < end_t
                        else:
                            # Ventana que cruza la medianoche (ej. 3:30 PM a 9:59 AM)
                            time_valid = current_t >= start_t or current_t < end_t

                        if time_valid:
                            logger.info("Se detectó ventana horaria activa y almuerzo pendiente. Iniciando Job de Almuerzo...")
                            run_lunch_automation_job(dry_run=False, gui_update_callback=gui_update_callback)
        except Exception as e:
            logger.error(f"Error en ciclo del planificador: {e}")

        # Esperar 60 segundos antes del siguiente chequeo
        time.sleep(60)


# ---------------------------------------------------------------------------
# Integración con el Programador de Tareas de Windows
# ---------------------------------------------------------------------------

def _get_task_action_path():
    """
    Determina dinámicamente la ruta del ejecutable o script para la tarea programada.

    Returns:
        Tupla (execute, arguments, working_dir) para la acción de la tarea.
    """
    if getattr(sys, 'frozen', False):
        # Corriendo como ejecutable compilado (.exe)
        exe_path = os.path.abspath(sys.executable)
        return exe_path, "--run-job", os.path.dirname(exe_path)
    else:
        # Corriendo desde el intérprete de Python: usar run_job.bat
        bat_path = os.path.join(BASE_DIR, "run_job.bat")
        if not os.path.exists(bat_path):
            raise FileNotFoundError(
                f"No se encontró el archivo run_job.bat.\n"
                f"Ruta esperada: {bat_path}\n"
                f"Este archivo es necesario para registrar la tarea programada "
                f"cuando se ejecuta desde código fuente."
            )
        return "cmd.exe", f'/c "{bat_path}"', BASE_DIR


def register_windows_task(trigger_hour=16, trigger_minute=30):
    """
    Registra una tarea diaria en el Programador de Tareas de Windows.
    Solicita elevación de privilegios (UAC) automáticamente.

    Args:
        trigger_hour: Hora del disparo diario (0-23).
        trigger_minute: Minuto del disparo diario (0-59).

    Returns:
        Tupla (success: bool, message: str).
    """
    try:
        execute, arguments, working_dir = _get_task_action_path()
    except FileNotFoundError as e:
        return False, str(e)

    trigger_time = f"{trigger_hour:02d}:{trigger_minute:02d}"
    logger.info(f"Registrando tarea Windows '{TASK_NAME}' para ejecutarse diariamente a las {trigger_time}...")

    transcript_log_path = os.path.join(BASE_DIR, "powershell_transcript.log")
    error_log_path = os.path.join(BASE_DIR, "powershell_error.txt")
    try:
        for p in [transcript_log_path, error_log_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        ps_script = (
            f"Start-Transcript -Path '{transcript_log_path}' -Force;\r\n"
            "$ErrorActionPreference = 'Stop';\r\n"
            "try {\r\n"
            f"    $action = New-ScheduledTaskAction -Execute '{execute}' -Argument '{arguments}' -WorkingDirectory '{working_dir}';\r\n"
            f"    $trigger = New-ScheduledTaskTrigger -Daily -At '{trigger_time}';\r\n"
            f"    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 10);\r\n"
            f"    Register-ScheduledTask -TaskName '{TASK_NAME}' -Trigger $trigger -Action $action -Settings $settings "
            f"-Description 'Job automatico diario para solicitar almuerzo en SiGCA' -Force;\r\n"
            "} catch {\r\n"
            f"    $_ | Out-File -FilePath '{error_log_path}' -Encoding utf8;\r\n"
            "}\r\n"
            "Stop-Transcript;\r\n"
        )
        # PowerShell espera la codificación UTF-16LE en Base64
        utf16_bytes = ps_script.encode("utf-16le")
        base64_cmd = base64.b64encode(utf16_bytes).decode("ascii")

        cmd = (
            f"Start-Process powershell -Verb RunAs -Wait -ArgumentList "
            f"'-NoProfile', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', '{base64_cmd}'"
        )
        logger.info(f"Lanzando proceso de elevación UAC para registro: Start-Process powershell ... -EncodedCommand")
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True, text=True, timeout=30
        )
        logger.info(f"UAC subprocess finalizado. stdout: '{result.stdout.strip()}', stderr: '{result.stderr.strip()}'")
    except Exception as e:
        logger.error(f"Error al iniciar script de registro de tarea: {e}")
        return False, str(e)

    # Verificar si la tarea se creó correctamente
    if check_windows_task_exists():
        msg = f"Tarea '{TASK_NAME}' registrada exitosamente para las {trigger_time}."
        logger.info(msg)
        return True, msg
    else:
        # Si falló, mostrar el log de errores y la transcripción de PowerShell
        if os.path.exists(error_log_path):
            try:
                with open(error_log_path, "r", encoding="utf-8") as f:
                    err_detail = f.read().strip()
                logger.error(f"Error detallado de PowerShell al registrar tarea:\n{err_detail}")
            except Exception as e:
                logger.error(f"No se pudo leer el archivo de error de PowerShell: {e}")

        if os.path.exists(transcript_log_path):
            try:
                with open(transcript_log_path, "r", encoding="utf-8") as f:
                    transcript_detail = f.read().strip()
                logger.error(f"Transcripción completa de PowerShell al registrar tarea:\n{transcript_detail}")
            except Exception as e:
                logger.error(f"No se pudo leer el archivo de transcripción de PowerShell: {e}")

        msg = f"No se pudo confirmar el registro de la tarea. Revisa los logs de PowerShell mostrados arriba."
        logger.warning(msg)
        return False, msg




def unregister_windows_task():
    """
    Elimina la tarea programada del Programador de Tareas de Windows.
    Solicita elevación de privilegios (UAC) automáticamente.

    Returns:
        Tupla (success: bool, message: str).
    """
    logger.info(f"Eliminando tarea Windows '{TASK_NAME}'...")

    import base64
    error_log_path = os.path.join(BASE_DIR, "powershell_error.txt")
    try:
        if os.path.exists(error_log_path):
            try:
                os.remove(error_log_path)
            except Exception:
                pass

        ps_script = (
            "$ErrorActionPreference = 'Stop';\r\n"
            "try {\r\n"
            f'    Unregister-ScheduledTask -TaskName "{TASK_NAME}" -Confirm:$false;\r\n'
            "} catch {\r\n"
            f"    $_ | Out-File -FilePath '{error_log_path}' -Encoding utf8;\r\n"
            "}\r\n"
        )
        # PowerShell espera la codificación UTF-16LE en Base64
        utf16_bytes = ps_script.encode("utf-16le")
        base64_cmd = base64.b64encode(utf16_bytes).decode("ascii")

        cmd = (
            f"Start-Process powershell -Verb RunAs -Wait -ArgumentList "
            f"'-NoProfile', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', '{base64_cmd}'"
        )
        logger.info(f"Lanzando proceso de elevación UAC para eliminación: Start-Process powershell ... -EncodedCommand")
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True, text=True, timeout=30
        )
        logger.info(f"UAC subprocess finalizado. stdout: '{result.stdout.strip()}', stderr: '{result.stderr.strip()}'")
    except Exception as e:
        logger.error(f"Error al iniciar script de eliminación de tarea: {e}")
        return False, str(e)

    # Mostrar detalles de error de PowerShell si existen
    if os.path.exists(error_log_path):
        try:
            with open(error_log_path, "r", encoding="utf-8") as f:
                err_detail = f.read().strip()
            logger.error(f"Error detallado de PowerShell al eliminar tarea:\n{err_detail}")
        except Exception as e:
            logger.error(f"No se pudo leer el archivo de error de PowerShell: {e}")

    if not check_windows_task_exists():
        msg = f"Tarea '{TASK_NAME}' eliminada exitosamente."
        logger.info(msg)
        return True, msg
    else:
        msg = "No se pudo confirmar la eliminación de la tarea. Revisa la consola de logs para ver la trazabilidad de PowerShell."
        logger.warning(msg)
        return False, msg



def check_windows_task_exists():
    """
    Verifica si la tarea programada existe en el Programador de Tareas.
    No requiere elevación de privilegios.

    Returns:
        True si la tarea existe, False en caso contrario.
    """
    try:
        # Intentar con schtasks para detectar existencia aunque sea denegado el acceso (SYSTEM task)
        result = subprocess.run(
            ["schtasks", "/query", "/tn", TASK_NAME],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return True
        if "Access is denied" in result.stderr or "Acceso denegado" in result.stderr:
            return True
        return False
    except Exception:
        return False


def get_windows_task_info():
    """
    Obtiene información detallada de la tarea programada.
    No requiere elevación de privilegios.

    Returns:
        Diccionario con información de la tarea o None si no existe.
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f'Get-ScheduledTask -TaskName "{TASK_NAME}" -ErrorAction Stop | '
             f'Select-Object TaskName, State | ConvertTo-Json'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            return json.loads(result.stdout.strip())
    except Exception:
        pass

    # Fallback si da acceso denegado (por ejemplo, tarea creada bajo SYSTEM en corridas previas)
    try:
        chk = subprocess.run(
            ["schtasks", "/query", "/tn", TASK_NAME],
            capture_output=True, text=True, timeout=5
        )
        if "Access is denied" in chk.stderr or "Acceso denegado" in chk.stderr:
            return {"TaskName": TASK_NAME, "State": "Ready (SYSTEM/Protected)"}
    except Exception:
        pass

    return None
