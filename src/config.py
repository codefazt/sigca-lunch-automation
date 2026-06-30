"""
Configuración centralizada del proyecto SiGCABot.
Maneja rutas base, constantes de la paleta de colores, persistencia de archivos
de configuración (.env, config.json, status.json) y auto-inicio con Windows.
"""

import os
import sys
import json
import ctypes
import threading
import winreg
import logging

logger = logging.getLogger("SiGCABot")

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
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

# ---------------------------------------------------------------------------
# Directorios Base
# ---------------------------------------------------------------------------

if getattr(sys, 'frozen', False):
    # Ejecutable empaquetado: datos del usuario junto al .exe
    BASE_DIR = os.path.dirname(sys.executable)
    # Recursos estáticos internos empaquetados por PyInstaller
    ASSET_DIR = sys._MEIPASS
else:
    # Desarrollo: el directorio raíz del proyecto (padre de src/)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSET_DIR = BASE_DIR

ENV_PATH = os.path.join(BASE_DIR, ".env")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
STATUS_PATH = os.path.join(BASE_DIR, "status.json")


def get_asset_path(filename):
    """Retorna la ruta absoluta a un recurso estático empaquetado."""
    return os.path.join(ASSET_DIR, filename)


# ---------------------------------------------------------------------------
# Paleta de Colores Oscura Premium (Estilo Catppuccin)
# ---------------------------------------------------------------------------

BG_MAIN = "#1e1e2e"
BG_CARD = "#252538"
BG_INPUT = "#313244"
FG_TEXT = "#cdd6f4"
FG_MUTED = "#a6adc8"
ACCENT = "#b4befe"
ACCENT_GREEN = "#a6e3a1"
ACCENT_RED = "#f38ba8"
ACCENT_YELLOW = "#f9e2af"
ACCENT_BLUE = "#89b4fa"

# ---------------------------------------------------------------------------
# Thread Safety
# ---------------------------------------------------------------------------

status_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Funciones de Persistencia — status.json
# ---------------------------------------------------------------------------

def load_status():
    """Carga el archivo status.json con protección de hilo."""
    with status_lock:
        if os.path.exists(STATUS_PATH):
            try:
                with open(STATUS_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "is_active": True,
            "last_successful_run": "",
            "last_run_timestamp": "Nunca",
            "last_run_status": "N/A",
            "startup_on_boot": False
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
    return {
        "start_hour": 15,
        "start_minute": 30,
        "end_hour": 10,
        "end_minute": 0,
        "timeout_ms": 30000,
        "headless": True,
        "retries": 3,
        "retry_delay_sec": 300,
        "prefer_menu": "saludable"
    }


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
    return env


def save_env_values(values):
    """Actualiza o añade claves en el archivo .env preservando comentarios."""
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
            if key in values:
                new_lines.append(f"{key}={values[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for key, val in values.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

# ---------------------------------------------------------------------------
# Auto-inicio con Windows (Registro del usuario actual)
# ---------------------------------------------------------------------------

def set_startup(enabled):
    """Registra o elimina la entrada de auto-inicio en el registro de Windows."""
    exe_path = os.path.abspath(sys.argv[0])
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    key_name = "SiGCALunchBot"

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            if exe_path.endswith(".exe"):
                winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                script_path = os.path.join(BASE_DIR, "app_gui.py")
                py_exe = sys.executable
                winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, f'"{py_exe}" "{script_path}"')
            logger.info("Auto-inicio registrado exitosamente.")
        else:
            try:
                winreg.DeleteValue(key, key_name)
                logger.info("Auto-inicio removido del registro.")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logger.error(f"Error al configurar inicio en registro de Windows: {e}")
        return False
