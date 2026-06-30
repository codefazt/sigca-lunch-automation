"""
Configuración centralizada del sistema de logging para SiGCABot.
Crea directorios necesarios (logs/, evidence/) y configura handlers
para archivo, consola y un handler especial para la GUI de Tkinter.
"""

import os
import sys
import logging

from src.config import BASE_DIR

# ---------------------------------------------------------------------------
# Crear directorios de salida
# ---------------------------------------------------------------------------

os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "evidence"), exist_ok=True)

# ---------------------------------------------------------------------------
# Configurar logging básico (archivo + consola)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(BASE_DIR, "logs", "lunch_automation.log"),
            encoding="utf-8"
        )
    ]
)

logger = logging.getLogger("SiGCABot")

# ---------------------------------------------------------------------------
# Handler especial para redirigir logs al widget de texto de la GUI
# ---------------------------------------------------------------------------

class GUILogHandler(logging.Handler):
    """
    Redirige registros de log al widget ScrolledText de Tkinter.
    Se conecta después de que la interfaz gráfica esté construida
    mediante el método connect().
    """

    def __init__(self):
        super().__init__()
        self._widget = None
        self._append_fn = None

    def connect(self, widget, append_fn):
        """
        Conecta el handler a un widget de Tkinter y una función de escritura.

        Args:
            widget: Referencia al widget Tkinter (para llamar .after())
            append_fn: Función callback(msg, levelname) para insertar texto
        """
        self._widget = widget
        self._append_fn = append_fn

    def emit(self, record):
        msg = self.format(record)
        if self._widget and self._append_fn:
            try:
                self._widget.after(0, self._append_fn, msg, record.levelname)
            except Exception:
                pass  # Widget destruido, ignorar


# Instancia global del handler de GUI (se conecta cuando la GUI se inicializa)
gui_log_handler = GUILogHandler()
gui_log_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
)
logging.getLogger().addHandler(gui_log_handler)
