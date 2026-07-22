"""
Configuración centralizada del proyecto SiGCABot.
Maneja rutas base, constantes de la paleta de colores, persistencia de archivos
de configuración (.env, config.json, status.json) y auto-inicio con Windows.
"""

import os
import sys
import json
import logging
import threading
import subprocess
from datetime import datetime
import ctypes
import base64

logger = logging.getLogger("SiGCABot")

# Versión global de la aplicación
APP_VERSION = "2.6.5"

# ---------------------------------------------------------------------------
# Ofuscación / Encriptación simple de campos sensibles
# ---------------------------------------------------------------------------

def obfuscate_text(text):
    """Ofusca/encripta texto de forma simple usando XOR y Base64."""
    if not text:
        return ""
    key = "SiGCABotSecureKey2026"
    xored = bytearray(c ^ ord(key[i % len(key)]) for i, c in enumerate(text.encode("utf-8")))
    return base64.b64encode(xored).decode("utf-8")

def deobfuscate_text(obfuscated):
    """Desofusca/desencripta texto obtenido con obfuscate_text."""
    if not obfuscated:
        return ""
    try:
        # Si el texto ya está ofuscado, debe ser base64 válido y descodificable
        # con la clave
        key = "SiGCABotSecureKey2026"
        data = base64.b64decode(obfuscated.encode("utf-8"), validate=True)
        xored = bytearray(b ^ ord(key[i % len(key)]) for i, b in enumerate(data))
        return xored.decode("utf-8")
    except Exception:
        # Si no es base64 válido o falla la descodificación, retornamos el texto
        # original para compatibilidad con .env sin ofuscar (texto plano)
        return obfuscated

# Credencial por defecto del remitente corporativo
DEFAULT_SMTP_PASSWORD_OBFUSCATED = "IQMzIWElBAc4RQcUGhNrAgFHUg=="

# ---------------------------------------------------------------------------
# Inicialización del entorno (se ejecuta al importar este módulo)
# ---------------------------------------------------------------------------

def hide_console():
    """Oculta la consola de comandos de Windows cuando corre como ejecutable compilado."""
    if getattr(sys, 'frozen', False):
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
        except Exception:
            pass

# Forzar a Playwright a usar los navegadores globales del usuario al correr compilado
# (Evita que busque en la carpeta temporal _MEIPASS de PyInstaller)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "ms-playwright"
)

# Redirigir stdout/stderr si no están disponibles (pythonw / PyInstaller --noconsole)
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
else:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass

if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')
else:
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Directorios Base
# ---------------------------------------------------------------------------

if getattr(sys, 'frozen', False):
    # Recursos estáticos internos empaquetados por PyInstaller
    ASSET_DIR = sys._MEIPASS
    # Ejecutable empaquetado: determinar si usamos modo portable (al lado del exe)
    # o modo persistente (en la carpeta AppData del usuario).
    exe_dir = os.path.dirname(sys.executable)
    if os.path.exists(os.path.join(exe_dir, "config.json")) or os.path.exists(os.path.join(exe_dir, ".env")):
        BASE_DIR = exe_dir
        logger.info(f"Modo portable detectado. Usando directorio del ejecutable: {BASE_DIR}")
    else:
        # Modo persistente por defecto
        appdata_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SiGCABot")
        os.makedirs(appdata_dir, exist_ok=True)
        BASE_DIR = appdata_dir
        logger.info(f"Modo persistente activado. Usando directorio AppData: {BASE_DIR}")
else:
    # Desarrollo: el directorio raíz del proyecto (padre de src/)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSET_DIR = BASE_DIR

ENV_PATH = os.path.join(BASE_DIR, ".env")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
STATUS_PATH = os.path.join(BASE_DIR, "status.json")

# Inicializar archivos por defecto en BASE_DIR si no existen
if not os.path.exists(ENV_PATH):
    template_path = os.path.join(ASSET_DIR, ".env.template")
    if os.path.exists(template_path):
        try:
            import shutil
            shutil.copy(template_path, ENV_PATH)
            logger.info(f"Archivo .env de plantilla inicializado en {ENV_PATH}")
        except Exception as e:
            logger.warning(f"No se pudo copiar .env.template a {ENV_PATH}: {e}")


def get_asset_path(filename):
    """Retorna la ruta absoluta a un recurso estático empaquetado."""
    return os.path.join(ASSET_DIR, filename)


# ---------------------------------------------------------------------------
# Paleta de Colores Oscura Premium (Estilo Hextech Client - LoL)
# ---------------------------------------------------------------------------

BG_MAIN = "#010a13"        # Fondo azul marino profundo (League of Legends)
BG_CARD = "#091428"        # Fondo de paneles y tarjetas
BG_INPUT = "#050c14"       # Fondo de cajas de entrada
FG_TEXT = "#f0e6d2"        # Texto dorado claro brillante
FG_MUTED = "#a09b8c"       # Texto dorado oscuro / grisáceo
ACCENT = "#c8aa6e"         # Oro Hextech pulido
ACCENT_GREEN = "#0acbe6"   # Azul rúnico brillante (Éxito / Activo)
ACCENT_RED = "#c83232"     # Rojo carmesí (Error / Parada forzada)
ACCENT_YELLOW = "#785a28"  # Oro oscuro/bronce (Advertencia)
ACCENT_BLUE = "#005a82"    # Azul mágico oscuro (Info)

# ---------------------------------------------------------------------------
# Thread Safety
# ---------------------------------------------------------------------------

status_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Cálculo del Ciclo Operativo de Almuerzo (target_lunch_date)
# ---------------------------------------------------------------------------

# Mapeo de weekday() de Python a nombres de días en español
DIAS_SEMANA_MAP = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo"
}

def get_target_lunch_date(now=None, config=None):
    """
    Calcula la fecha del almuerzo objetivo basándose en el ciclo operativo real.

    El formulario de SiGCA abre a la hora de inicio (ej. 15:30) para solicitar
    el almuerzo del DÍA SIGUIENTE. Permanece abierto hasta la hora de fin
    (ej. 10:00 AM) de ese día siguiente.

    - Si hora_actual >= start_hour:start_minute → target = mañana
    - Si hora_actual < end_hour:end_minute     → target = hoy (mismo ciclo)
    - Si hora_actual está en el "hueco" entre end y start → target = mañana
      (el próximo ciclo que abrirá a las start_hour)

    Args:
        now: datetime opcional. Si es None, usa datetime.now().
        config: dict opcional con start_hour, start_minute, end_hour, end_minute.

    Returns:
        Tupla (target_date: date, day_name_es: str)
        Ejemplo: (date(2026, 7, 23), "Miércoles")
    """
    from datetime import timedelta, time as dt_time
    if now is None:
        now = datetime.now()
    if config is None:
        config = load_config()

    start_t = dt_time(
        config.get("start_hour", 15),
        config.get("start_minute", 30)
    )
    end_t = dt_time(
        config.get("end_hour", 10),
        config.get("end_minute", 0)
    )
    current_t = now.time()

    if start_t <= end_t:
        # Ventana en el mismo día (ej. 07:30 a 10:00)
        # Si estamos dentro o después del inicio → almuerzo es para mañana
        if current_t >= start_t:
            target = (now + timedelta(days=1)).date()
        else:
            # Antes del inicio: si estamos antes del cierre, sigue el mismo ciclo (hoy)
            # Si estamos después del cierre, el próximo ciclo abre a start_t → target mañana
            if current_t < end_t:
                target = now.date()
            else:
                target = (now + timedelta(days=1)).date()
    else:
        # Ventana que cruza la medianoche (ej. 15:30 a 10:00)
        if current_t >= start_t:
            # Después de las 15:30 → almuerzo es para mañana
            target = (now + timedelta(days=1)).date()
        elif current_t < end_t:
            # Antes de las 10:00 AM (madrugada/mañana) → almuerzo sigue siendo para hoy
            target = now.date()
        else:
            # En el "hueco" entre 10:00 AM y 15:30 (fuera de ventana)
            # El próximo ciclo abrirá a las 15:30 → target será mañana
            target = (now + timedelta(days=1)).date()

    day_name_es = DIAS_SEMANA_MAP.get(target.weekday(), "")
    return target, day_name_es

# ---------------------------------------------------------------------------
# Funciones de Persistencia — status.json
# ---------------------------------------------------------------------------

def load_status():
    """Carga el archivo status.json con protección de hilo."""
    with status_lock:
        if os.path.exists(STATUS_PATH):
            try:
                with open(STATUS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Realizar auto-limpieza si cambió el día
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    changed = False
                    
                    # Limpiar cancelaciones si es otro día
                    cancel_date = data.get("last_cancellation_date", "")
                    if cancel_date and cancel_date != today_str:
                        data["last_cancellation_date"] = ""
                        data["cancellations_count"] = 0
                        data["is_cancelled_today"] = False
                        changed = True
                        
                    # Si no tiene el campo is_cancelled_today, inicializarlo
                    if "is_cancelled_today" not in data:
                        data["is_cancelled_today"] = False
                        changed = True

                    # Inicializar last_successful_target_date para compatibilidad
                    if "last_successful_target_date" not in data:
                        data["last_successful_target_date"] = ""
                        changed = True
                        
                    if changed:
                        try:
                            with open(STATUS_PATH, "w", encoding="utf-8") as fw:
                                json.dump(data, fw, indent=2, ensure_ascii=False)
                        except Exception:
                            pass
                    return data
            except Exception:
                pass
        return {
            "is_active": True,
            "last_successful_run": "",
            "last_successful_target_date": "",
            "last_run_timestamp": "Nunca",
            "last_run_status": "N/A",
            "startup_on_boot": False,
            "cancellations_count": 0,
            "last_cancellation_date": "",
            "is_cancelled_today": False,
            "last_cleanup_date": ""
        }


def save_status(data):
    """Guarda el archivo status.json con protección de hilo."""
    with status_lock:
        try:
            with open(STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error al guardar status.json: {e}")

# ---------------------------------------------------------------------------
# Funciones de Persistencia — config.json
# ---------------------------------------------------------------------------

def load_config():
    """Carga el archivo config.json o retorna valores por defecto."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
            
    # Si no existe, crear el archivo config.json por defecto en CONFIG_PATH
    default_config = {
        "start_hour": 15,
        "start_minute": 30,
        "end_hour": 10,
        "end_minute": 0,
        "timeout_ms": 30000,
        "headless": True,
        "retries": 3,
        "retry_delay_sec": 300,
        "prefer_menu": "saludable",
        "disabled_days": [],
        "questionnaire": {
            "ubicacion": "Sede ExCle",
            "estrellas": "3",
            "bien_cocidos": "last",
            "porcion_acorde": "last",
            "condimentacion": 1,
            "asistir_tarde": "Sí",
            "comentario": "Favor quitar el jugo de melon y las porciones no tienen suficiente proteina, quedando uno con hambre"
        }
    }
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        logger.info(f"Archivo config.json por defecto inicializado en {CONFIG_PATH}")
    except Exception as e:
        logger.error(f"No se pudo inicializar config.json en {CONFIG_PATH}: {e}")
        
    return default_config


def save_config(data):
    """Guarda el archivo config.json."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error al guardar config.json: {e}")

# ---------------------------------------------------------------------------
# Funciones de Persistencia — .env
# ---------------------------------------------------------------------------

def load_env_dict():
    """Lee el archivo .env y retorna un diccionario clave-valor."""
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
                    
    # Desofuscar campos sensibles
    if "SIGCA_PASSWORDS" in env:
        env["SIGCA_PASSWORDS"] = deobfuscate_text(env["SIGCA_PASSWORDS"])
    if "TELEGRAM_TOKEN" in env:
        env["TELEGRAM_TOKEN"] = deobfuscate_text(env["TELEGRAM_TOKEN"])
        
    return env


def save_env_values(values):
    """Actualiza o añade claves en el archivo .env preservando comentarios."""
    values_copy = values.copy()
    
    # Ofuscar campos sensibles antes de guardar
    if "SIGCA_PASSWORDS" in values_copy:
        values_copy["SIGCA_PASSWORDS"] = obfuscate_text(values_copy["SIGCA_PASSWORDS"])
    if "TELEGRAM_TOKEN" in values_copy:
        values_copy["TELEGRAM_TOKEN"] = obfuscate_text(values_copy["TELEGRAM_TOKEN"])

    current_lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            current_lines = f.readlines()

    updated_keys = set()
    new_lines = []
    for line in current_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        if "=" in line:
            key, _ = line.split("=", 1)
            key = key.strip()
            if key in values_copy:
                new_lines.append(f"{key}={values_copy[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for key, val in values_copy.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

# ---------------------------------------------------------------------------
# Auto-inicio con Windows (Registro HKCU + Carpeta Startup + Auto-Healing)
# ---------------------------------------------------------------------------

def get_expected_startup_command():
    """Retorna la cadena exacta del comando que debe registrarse en el Auto-Inicio de Windows."""
    if getattr(sys, 'frozen', False):
        exe_path = os.path.abspath(sys.executable)
        return f'"{exe_path}"'
    else:
        script_path = os.path.join(BASE_DIR, "app_gui.py")
        py_exe = os.path.abspath(sys.executable)
        return f'"{py_exe}" "{script_path}"'


def sync_startup_shortcut(enabled):
    """
    Crea o elimina el acceso directo de respaldo en la carpeta Startup de Windows.
    Ruta: %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\SiGCABot.lnk
    """
    if os.name != 'nt':
        return False

    try:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return False

        startup_folder = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
        if not os.path.exists(startup_folder):
            try:
                os.makedirs(startup_folder, exist_ok=True)
            except Exception:
                return False

        shortcut_path = os.path.join(startup_folder, "SiGCABot.lnk")

        if enabled:
            if getattr(sys, 'frozen', False):
                target = os.path.abspath(sys.executable)
                args = ""
                work_dir = os.path.dirname(target)
            else:
                target = os.path.abspath(sys.executable)
                script_path = os.path.join(BASE_DIR, "app_gui.py")
                args = f'"{script_path}"'
                work_dir = BASE_DIR

            # Escapar comillas simples para evitar roturas de sintaxis en PowerShell si hay espacios o caracteres especiales en la ruta
            sh_path_esc = shortcut_path.replace("'", "''")
            target_esc = target.replace("'", "''")
            args_esc = args.replace("'", "''")
            work_dir_esc = work_dir.replace("'", "''")

            ps_cmd = (
                f"$WshShell = New-Object -ComObject WScript.Shell; "
                f"$Shortcut = $WshShell.CreateShortcut('{sh_path_esc}'); "
                f"$Shortcut.TargetPath = '{target_esc}'; "
                f"$Shortcut.Arguments = '{args_esc}'; "
                f"$Shortcut.WorkingDirectory = '{work_dir_esc}'; "
                f"$Shortcut.Save()"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            logger.info(f"Acceso directo de auto-inicio sincronizado en: {shortcut_path}")
        else:
            if os.path.exists(shortcut_path):
                try:
                    os.remove(shortcut_path)
                    logger.info(f"Acceso directo de auto-inicio eliminado de: {shortcut_path}")
                except Exception:
                    pass
        return True
    except Exception as e:
        logger.warning(f"No se pudo sincronizar el acceso directo de Inicio: {e}")
        return False


def set_startup(enabled):
    """
    Registra o elimina la entrada de auto-inicio en el Registro de Windows y en la carpeta Startup.
    """
    if os.name != 'nt':
        return False

    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    key_name = "SiGCALunchBot"
    expected_cmd = get_expected_startup_command()

    success = False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, expected_cmd)
            logger.info(f"Auto-inicio registrado exitosamente en Registro de Windows: {expected_cmd}")
        else:
            try:
                winreg.DeleteValue(key, key_name)
                logger.info("Auto-inicio removido del Registro de Windows.")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        success = True
    except Exception as e:
        logger.error(f"Error al configurar inicio en Registro de Windows: {e}")

    # Sincronizar también en la carpeta Startup como respaldo
    sync_startup_shortcut(enabled)
    return success


def check_and_repair_startup():
    """
    Inspecciona si el auto-inicio debe estar activo (según status.json).
    Verifica que la clave en el registro exista y coincida con la ruta actual.
    Si la clave no existe o la ruta cambió, la repara automáticamente (Auto-Healing).
    """
    if os.name != 'nt':
        return False

    try:
        status_info = load_status()
        should_be_enabled = status_info.get("startup_on_boot", False)

        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key_name = "SiGCALunchBot"
        expected_cmd = get_expected_startup_command()

        current_val = None
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            current_val, _ = winreg.QueryValueEx(key, key_name)
            winreg.CloseKey(key)
        except (FileNotFoundError, OSError):
            current_val = None

        if should_be_enabled:
            # Si debe estar activado, comprobar si el valor es diferente o falta
            if current_val != expected_cmd:
                logger.info(f"⚠️ Desincronización detectada en Auto-Inicio. Registro actual: '{current_val}', Esperado: '{expected_cmd}'. Ejecutando Auto-Healing...")
                set_startup(True)
                return True
            else:
                # Asegurar que el acceso directo de respaldo en Startup también exista
                sync_startup_shortcut(True)
        else:
            # Si debe estar desactivado pero la clave o acceso directo existen, limpiarlos
            if current_val is not None:
                logger.info("⚠️ Auto-Inicio desactivado en status.json pero presente en el Registro. Limpiando...")
                set_startup(False)
                return True
            else:
                sync_startup_shortcut(False)
    except Exception as e:
        logger.error(f"Error durante el chequeo y auto-reparación de Auto-Inicio: {e}")
    return False

