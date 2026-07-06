"""
SiGCABot — Aplicación de escritorio para automatización de almuerzos en SiGCA.

Punto de entrada principal de la aplicación. Soporta dos modos de ejecución:
    1. Modo GUI (por defecto): Interfaz gráfica de escritorio con panel de control.
    2. Modo CLI (--run-job): Ejecución directa del bot sin interfaz gráfica,
       utilizado por el Programador de Tareas de Windows.

Uso:
    python app_gui.py                        → Abre la GUI
    python app_gui.py --run-job              → Ejecuta el bot en modo consola
    python app_gui.py --run-job --dry-run    → Simulación en modo consola
    python app_gui.py --run-job --force-time → Ignora validación horaria
    python app_gui.py --cancel-order         → Cancela el pedido del día
"""

import os
import sys
import argparse

# --- Parseo temprano de argumentos para decidir el modo de ejecución ---

def _parse_args():
    parser = argparse.ArgumentParser(
        description="SiGCABot — Automatización de solicitud de almuerzo en SiGCA."
    )
    parser.add_argument("--run-job", action="store_true",
                        help="Ejecutar el bot directamente sin interfaz gráfica (modo consola).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simular el flujo completo sin confirmar el pedido final.")
    parser.add_argument("--force-time", action="store_true",
                        help="Ignorar la validación del rango horario.")
    parser.add_argument("--cancel-order", action="store_true",
                        help="Cancelar la solicitud de almuerzo del día.")
    parser.add_argument("--check-deps", action="store_true",
                        help="Verificar dependencias y operatividad del navegador.")
    return parser.parse_args()


_args = _parse_args()

# ---------------------------------------------------------------------------
# Modo CLI (--run-job, --cancel-order o --check-deps): Sin GUI
# ---------------------------------------------------------------------------

if _args.run_job or _args.cancel_order or _args.check_deps:
    # Importar módulos de infraestructura
    from src.config import BASE_DIR, load_status, save_status
    from src.logger import logger
    from src.bot_engine import LunchBot
    from datetime import datetime

    if _args.check_deps:
        try:
            # Forzar a Playwright a usar los navegadores globales del usuario al correr compilado
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
                os.path.expanduser("~"), "AppData", "Local", "ms-playwright"
            )
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, timeout=4000)
                browser.close()
            print("OK_PLAYWRIGHT")
            sys.exit(0)
        except Exception as e:
            print(f"ERROR_PLAYWRIGHT: {e}")
            sys.exit(1)

    elif _args.run_job:
        logger.info("Iniciando ejecución de LunchBot en modo CLI (--run-job)...")
        try:
            bot = LunchBot()
            if _args.force_time:
                bot.is_time_valid = lambda *a, **k: True
                logger.info("Validación horaria forzada (desactivada).")
            exit_code, msg, evidence = bot.run_automation(dry_run=_args.dry_run)
            
            # Guardar el resultado en status.json
            try:
                status_info = load_status()
                status_info["last_run_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if exit_code == 0:
                    status_info["last_run_status"] = "success"
                    if not _args.dry_run:
                        status_info["last_successful_run"] = datetime.now().strftime("%Y-%m-%d")
                else:
                    status_info["last_run_status"] = f"error (código {exit_code})"
                    if exit_code == 1:
                        status_info["is_active"] = False  # Desactivar si falla contraseña para evitar bloqueo
                save_status(status_info)
            except Exception as se:
                logger.error(f"No se pudo guardar el estado en status.json: {se}")

            logger.info(f"Ejecución completada: {msg} (código: {exit_code})")
            sys.exit(exit_code)
        except Exception as e:
            logger.critical(f"Error crítico no controlado: {e}", exc_info=True)
            sys.exit(5)

    elif _args.cancel_order:
        logger.info("Iniciando cancelación de almuerzo en modo CLI (--cancel-order)...")
        try:
            bot = LunchBot()
            exit_code, msg, evidence = bot.cancel_lunch_order()
            
            # Guardar el resultado en status.json en caso de éxito
            if exit_code == 0:
                try:
                    status_info = load_status()
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    c_count = status_info.get("cancellations_count", 0)
                    if status_info.get("last_cancellation_date") != today_str:
                        c_count = 0
                    c_count += 1
                    status_info["cancellations_count"] = c_count
                    status_info["last_cancellation_date"] = today_str
                    status_info["is_cancelled_today"] = True
                    status_info["last_run_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    status_info["last_run_status"] = "cancelado"
                    if "last_successful_run" in status_info:
                        status_info["last_successful_run"] = ""
                    save_status(status_info)
                except Exception as se:
                    logger.error(f"No se pudo guardar el estado de cancelación en status.json: {se}")

            logger.info(f"Cancelación completada: {msg} (código: {exit_code})")
            sys.exit(exit_code)
        except Exception as e:
            logger.critical(f"Error crítico no controlado: {e}", exc_info=True)
            sys.exit(5)

# ---------------------------------------------------------------------------
# Modo GUI (por defecto): Interfaz gráfica de escritorio
# ---------------------------------------------------------------------------

from src.config import BASE_DIR, load_env_dict, save_env_values, load_config, save_config, get_asset_path, set_startup, BG_MAIN, BG_CARD, BG_INPUT, FG_TEXT, FG_MUTED, ACCENT, ACCENT_GREEN, ACCENT_RED, ACCENT_YELLOW, ACCENT_BLUE, load_status, save_status
from src.logger import logger, gui_log_handler
from src.bot_engine import LunchBot, kill_playwright_orphans
from src.health_server import start_http_server
from src.telegram_poller import start_telegram_poller
from src.scheduler import (
    start_scheduler, run_lunch_automation_job,
    register_windows_task, unregister_windows_task, check_windows_task_exists,
)
from src.notifications import send_telegram_message
from src import state

# Ocultar consola en modo compilado (solo para GUI)
from src.config import hide_console
hide_console()

import html
import threading
import subprocess
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import pystray

# ---------------------------------------------------------------------------
# Estado global de la GUI
# ---------------------------------------------------------------------------

app = None
tray_icon = None

# ---------------------------------------------------------------------------
# Funciones auxiliares de la GUI
# ---------------------------------------------------------------------------

def append_log_gui(msg, level):
    """Inserta una línea de log en el widget ScrolledText de la consola.
    Recorta automáticamente las líneas más antiguas para evitar fugas de memoria."""
    if app and app.log_text:
        app.log_text.configure(state="normal")
        tag = level.lower()
        app.log_text.insert("end", msg + "\n", tag)

        # Limitar a 500 líneas para evitar congelamiento de la GUI por acumulación
        MAX_LOG_LINES = 500
        line_count = int(app.log_text.index("end-1c").split(".")[0])
        if line_count > MAX_LOG_LINES:
            app.log_text.delete("1.0", f"{line_count - MAX_LOG_LINES}.0")

        app.log_text.configure(state="disabled")
        app.log_text.see("end")


def update_gui_status_badge():
    """Refresca los indicadores de estado en el sidebar (thread-safe)."""
    if not app:
        return
    app.root.after(0, _update_gui_status_badge_sync)


def _update_gui_status_badge_sync():
    if not app:
        return
    status_info = load_status()
    is_act = status_info.get("is_active", True)
    init_text = "ACTIVO" if is_act else "INACTIVO"
    init_bg = ACCENT_GREEN if is_act else ACCENT_RED

    if hasattr(app, "status_badge") and app.status_badge.winfo_exists():
        app.status_badge.configure(text=init_text, bg=init_bg)
        if is_act:
            app.toggle_btn.configure(text="Desactivar Bot", bg=ACCENT_RED, activebackground="#f3a8b8")
        else:
            app.toggle_btn.configure(text="Activar Bot", bg=ACCENT_GREEN, activebackground="#a6f3b0")

    # Actualizar labels e historial de estado
    if hasattr(app, "last_run_lbl") and app.last_run_lbl.winfo_exists():
        lr_date = status_info.get("last_run_timestamp", "Nunca")
        app.last_run_lbl.configure(text=f"Último pedido:\n{lr_date}")
    if hasattr(app, "last_status_lbl") and app.last_status_lbl.winfo_exists():
        app.last_status_lbl.configure(text=f"Resultado: {status_info.get('last_run_status', 'N/A')}")
        
    # Refrescar conteo y UI de cancelación
    if hasattr(app, "cancel_count_lbl") and app.cancel_count_lbl.winfo_exists():
        c_count = status_info.get("cancellations_count", 0)
        today_str = datetime.now().strftime("%Y-%m-%d")
        if status_info.get("last_cancellation_date") != today_str:
            c_count = 0
        app.cancel_count_lbl.configure(text=f"Cancelaciones hoy: {c_count}/3")
        
    if hasattr(app, "cancelled_var") and app.cancelled_chk.winfo_exists():
        app.cancelled_var.set(status_info.get("is_cancelled_today", False))
        
    if hasattr(app, "cancel_date_lbl") and app.cancel_date_lbl.winfo_exists():
        cancel_date = status_info.get("last_cancellation_date", "")
        app.cancel_date_lbl.configure(text=f"Cancelado el: {cancel_date}" if cancel_date else "Cancelado el: N/A")


# ---------------------------------------------------------------------------
# Cuadros de diálogo Premium
# ---------------------------------------------------------------------------

class PremiumMessageBox(tk.Toplevel):
    """Ventana modal personalizada con estilo premium oscuro."""

    def __init__(self, parent, title, message, alert_type="info"):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG_MAIN)
        self.resizable(False, False)
        self.transient(parent)
        self.withdraw()

        if alert_type == "info":
            color, icon_char = ACCENT_BLUE, "ℹ"
        elif alert_type == "success":
            color, icon_char = ACCENT_GREEN, "✓"
        elif alert_type == "warning":
            color, icon_char = ACCENT_YELLOW, "⚠"
        elif alert_type == "error":
            color, icon_char = ACCENT_RED, "❌"
        else:
            color, icon_char = ACCENT, "ℹ"

        self.overrideredirect(True)

        outer_frame = tk.Frame(self, bg=color, bd=2)
        outer_frame.pack(fill="both", expand=True)

        inner_frame = tk.Frame(outer_frame, bg=BG_CARD, padx=22, pady=22)
        inner_frame.pack(fill="both", expand=True)

        # Header
        header_frame = tk.Frame(inner_frame, bg=BG_CARD)
        header_frame.pack(fill="x", pady=(0, 15))

        title_lbl = tk.Label(header_frame, text=title, font=("Segoe UI", 12, "bold"), fg=FG_TEXT, bg=BG_CARD)
        title_lbl.pack(side="left")

        close_btn = tk.Label(header_frame, text="✕", font=("Segoe UI", 12, "bold"), fg=FG_MUTED, bg=BG_CARD, cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.destroy())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg=ACCENT_RED))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg=FG_MUTED))

        # Contenido
        content_frame = tk.Frame(inner_frame, bg=BG_CARD)
        content_frame.pack(fill="both", expand=True, pady=(0, 20))

        canvas_size = 48
        icon_canvas = tk.Canvas(content_frame, width=canvas_size, height=canvas_size, bg=BG_CARD, highlightthickness=0)
        icon_canvas.pack(side="left", padx=(0, 15), anchor="n")
        icon_canvas.create_oval(2, 2, canvas_size-2, canvas_size-2, fill=BG_INPUT, outline=color, width=2)
        icon_canvas.create_text(canvas_size/2, canvas_size/2, text=icon_char, fill=color, font=("Segoe UI", 18, "bold"))

        msg_lbl = tk.Label(content_frame, text=message, font=("Segoe UI", 10), fg=FG_TEXT, bg=BG_CARD, justify="left", wraplength=320)
        msg_lbl.pack(side="left", fill="both", expand=True, anchor="w")

        # Botón Aceptar
        btn_frame = tk.Frame(inner_frame, bg=BG_CARD)
        btn_frame.pack(fill="x")

        ok_btn = tk.Button(btn_frame, text="Aceptar", font=("Segoe UI", 10, "bold"), bg=color, fg="#11111b", bd=0, padx=25, pady=6, cursor="hand2", activeforeground="#11111b", activebackground=color, command=self.destroy)
        ok_btn.pack(side="right")

        ok_btn.bind("<Enter>", lambda e: ok_btn.configure(bg=self._darken(color, 0.15)))
        ok_btn.bind("<Leave>", lambda e: ok_btn.configure(bg=color))

        # Centrar ventana
        self.update_idletasks()
        width = 420
        height = inner_frame.winfo_reqheight() + 4
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()

        try:
            if parent and parent.winfo_viewable():
                px, py = parent.winfo_rootx(), parent.winfo_rooty()
                pw, ph = parent.winfo_width(), parent.winfo_height()
                if px < -10000 or py < -10000 or px > sw or py > sh:
                    raise ValueError
                x = px + (pw - width) // 2
                y = py + (ph - height) // 2
            else:
                raise ValueError
        except Exception:
            x = (sw - width) // 2
            y = (sh - height) // 2

        if x < 0 or x + width > sw:
            x = max(0, (sw - width) // 2)
        if y < 0 or y + height > sh:
            y = max(0, (sh - height) // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        self.update()
        self.grab_set()

        # Soporte para arrastrar
        self.drag_data = {"x": 0, "y": 0}
        header_frame.bind("<ButtonPress-1>", self._start_drag)
        header_frame.bind("<B1-Motion>", self._drag)
        inner_frame.bind("<ButtonPress-1>", self._start_drag)
        inner_frame.bind("<B1-Motion>", self._drag)

        self.bind("<Return>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())

    def destroy(self):
        try:
            self.grab_release()
        except Exception:
            pass
        if self.master:
            try:
                self.master.focus_set()
            except Exception:
                pass
        super().destroy()

    def _start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def _drag(self, event):
        x = self.winfo_x() + event.x - self.drag_data["x"]
        y = self.winfo_y() + event.y - self.drag_data["y"]
        self.geometry(f"+{x}+{y}")

    @staticmethod
    def _darken(hex_color, factor):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(max(0, int(c * (1 - factor))) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"


def show_custom_info(title, message):
    if app and app.root:
        dialog = PremiumMessageBox(app.root, title, message, "info")
        app.root.wait_window(dialog)
    else:
        messagebox.showinfo(title, message)

def show_custom_success(title, message):
    if app and app.root:
        dialog = PremiumMessageBox(app.root, title, message, "success")
        app.root.wait_window(dialog)
    else:
        messagebox.showinfo(title, message)

def show_custom_error(title, message):
    if app and app.root:
        dialog = PremiumMessageBox(app.root, title, message, "error")
        app.root.wait_window(dialog)
    else:
        messagebox.showerror(title, message)

def show_custom_warning(title, message):
    if app and app.root:
        dialog = PremiumMessageBox(app.root, title, message, "warning")
        app.root.wait_window(dialog)
    else:
        messagebox.showwarning(title, message)


class PremiumConfirmBox(tk.Toplevel):
    """Ventana modal de confirmación personalizada con estilo premium oscuro."""

    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.result = False
        self.title(title)
        self.configure(bg=BG_MAIN)
        self.resizable(False, False)
        self.transient(parent)
        self.withdraw()

        color, icon_char = ACCENT_BLUE, "?"
        self.overrideredirect(True)

        outer_frame = tk.Frame(self, bg=color, bd=2)
        outer_frame.pack(fill="both", expand=True)

        inner_frame = tk.Frame(outer_frame, bg=BG_CARD, padx=22, pady=22)
        inner_frame.pack(fill="both", expand=True)

        # Header
        header_frame = tk.Frame(inner_frame, bg=BG_CARD)
        header_frame.pack(fill="x", pady=(0, 15))

        title_lbl = tk.Label(header_frame, text=title, font=("Segoe UI", 12, "bold"), fg=FG_TEXT, bg=BG_CARD)
        title_lbl.pack(side="left")

        close_btn = tk.Label(header_frame, text="✕", font=("Segoe UI", 12, "bold"), fg=FG_MUTED, bg=BG_CARD, cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.on_no())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg=ACCENT_RED))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg=FG_MUTED))

        # Contenido
        content_frame = tk.Frame(inner_frame, bg=BG_CARD)
        content_frame.pack(fill="both", expand=True, pady=(0, 20))

        canvas_size = 48
        icon_canvas = tk.Canvas(content_frame, width=canvas_size, height=canvas_size, bg=BG_CARD, highlightthickness=0)
        icon_canvas.pack(side="left", padx=(0, 15), anchor="n")
        icon_canvas.create_oval(2, 2, canvas_size-2, canvas_size-2, fill=BG_INPUT, outline=color, width=2)
        icon_canvas.create_text(canvas_size/2, canvas_size/2, text=icon_char, fill=color, font=("Segoe UI", 18, "bold"))

        msg_lbl = tk.Label(content_frame, text=message, font=("Segoe UI", 10), fg=FG_TEXT, bg=BG_CARD, justify="left", wraplength=320)
        msg_lbl.pack(side="left", fill="both", expand=True, anchor="w")

        # Botones
        btn_frame = tk.Frame(inner_frame, bg=BG_CARD)
        btn_frame.pack(fill="x")

        # Botón No
        no_btn = tk.Button(btn_frame, text="No", font=("Segoe UI", 10, "bold"), bg=BG_INPUT, fg=FG_TEXT, bd=0, padx=25, pady=6, cursor="hand2", activeforeground=FG_TEXT, activebackground=BG_INPUT, command=self.on_no)
        no_btn.pack(side="right")
        no_btn.bind("<Enter>", lambda e: no_btn.configure(bg=self._darken(BG_INPUT, 0.15)))
        no_btn.bind("<Leave>", lambda e: no_btn.configure(bg=BG_INPUT))

        # Botón Sí
        yes_btn = tk.Button(btn_frame, text="Sí", font=("Segoe UI", 10, "bold"), bg=ACCENT_BLUE, fg="#11111b", bd=0, padx=25, pady=6, cursor="hand2", activeforeground="#11111b", activebackground=ACCENT_BLUE, command=self.on_yes)
        yes_btn.pack(side="right", padx=(0, 10))
        yes_btn.bind("<Enter>", lambda e: yes_btn.configure(bg=self._darken(ACCENT_BLUE, 0.15)))
        yes_btn.bind("<Leave>", lambda e: yes_btn.configure(bg=ACCENT_BLUE))

        # Centrar ventana
        self.update_idletasks()
        width = 420
        height = inner_frame.winfo_reqheight() + 4
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()

        try:
            if parent and parent.winfo_viewable():
                px, py = parent.winfo_rootx(), parent.winfo_rooty()
                pw, ph = parent.winfo_width(), parent.winfo_height()
                if px < -10000 or py < -10000 or px > sw or py > sh:
                    raise ValueError
                x = px + (pw - width) // 2
                y = py + (ph - height) // 2
            else:
                raise ValueError
        except Exception:
            x = (sw - width) // 2
            y = (sh - height) // 2

        if x < 0 or x + width > sw:
            x = max(0, (sw - width) // 2)
        if y < 0 or y + height > sh:
            y = max(0, (sh - height) // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        self.update()
        self.grab_set()

        # Soporte para arrastrar
        self.drag_data = {"x": 0, "y": 0}
        header_frame.bind("<ButtonPress-1>", self._start_drag)
        header_frame.bind("<B1-Motion>", self._drag)
        inner_frame.bind("<ButtonPress-1>", self._start_drag)
        inner_frame.bind("<B1-Motion>", self._drag)

        self.bind("<Return>", lambda e: self.on_yes())
        self.bind("<Escape>", lambda e: self.on_no())

    def on_yes(self):
        self.result = True
        self.destroy()

    def on_no(self):
        self.result = False
        self.destroy()

    def destroy(self):
        try:
            self.grab_release()
        except Exception:
            pass
        if self.master:
            try:
                self.master.focus_set()
            except Exception:
                pass
        super().destroy()

    def _start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def _drag(self, event):
        x = self.winfo_x() + event.x - self.drag_data["x"]
        y = self.winfo_y() + event.y - self.drag_data["y"]
        self.geometry(f"+{x}+{y}")

    @staticmethod
    def _darken(hex_color, factor):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(max(0, int(c * (1 - factor))) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"


def show_custom_confirm(title, message):
    if app and app.root:
        dialog = PremiumConfirmBox(app.root, title, message)
        app.root.wait_window(dialog)
        return dialog.result
    else:
        return messagebox.askyesno(title, message)


# ---------------------------------------------------------------------------
# Clase Principal de la GUI
# ---------------------------------------------------------------------------

class AppGUI:
    def __init__(self, root):
        global app
        app = self
        self.root = root
        self.root.title("SiGCA Lunch Automation Panel")
        self.root.geometry("1000x650")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        # Variables de estado del subproceso
        self.active_subprocess = None
        self.subprocess_start_time = 0
        self.subprocess_type = None
        self.subprocess_output_lines = []

        self.setup_styles()
        self.create_layout()
        self.load_settings_into_inputs()
        update_gui_status_badge()

        # Conectar el handler de logs a la GUI
        gui_log_handler.connect(self.log_text, append_log_gui)

        logger.info("Aplicación iniciada. Bienvenido al panel de SiGCA Bot.")

        # Programar la verificación de dependencias de Playwright al inicio
        self.root.after(100, self.verify_dependencies_startup)

    # --- Estilos ---

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG_MAIN, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_CARD, foreground=FG_TEXT, padding=[15, 6], font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", BG_MAIN)], foreground=[("selected", ACCENT)])

    # --- Layout Principal ---

    def create_layout(self):
        # 1. Sidebar (Izquierda)
        self.sidebar = tk.Frame(self.root, bg=BG_CARD, width=240, bd=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Imagen de Bender (escalada a 120x120 para optimizar espacio vertical)
        img_path = get_asset_path("bender_chef.png")
        if os.path.exists(img_path):
            try:
                raw_img = Image.open(img_path)
                resized = raw_img.resize((120, 120), Image.Resampling.LANCZOS)
                self.bender_img = ImageTk.PhotoImage(resized)
                img_lbl = tk.Label(self.sidebar, image=self.bender_img, bg=BG_CARD)
                img_lbl.pack(pady=(10, 5))
            except Exception as e:
                logger.error(f"Error cargando imagen bender: {e}")
        else:
            lbl = tk.Label(self.sidebar, text="🤖 LunchBot", fg=ACCENT, bg=BG_CARD, font=("Segoe UI", 16, "bold"))
            lbl.pack(pady=15)

        title_lbl = tk.Label(self.sidebar, text="SiGCA Lunch Bot", fg=FG_TEXT, bg=BG_CARD, font=("Segoe UI", 12, "bold"))
        title_lbl.pack()

        version_lbl = tk.Label(self.sidebar, text="Versión 2.2.0", fg=FG_MUTED, bg=BG_CARD, font=("Segoe UI", 8))
        version_lbl.pack(pady=(0, 5))

        sep = tk.Frame(self.sidebar, height=1, bg=BG_INPUT)
        sep.pack(fill="x", padx=20, pady=5)

        # Badge de Estado
        state_title = tk.Label(self.sidebar, text="ESTADO DEL SERVICIO", fg=FG_MUTED, bg=BG_CARD, font=("Segoe UI", 8, "bold"))
        state_title.pack(pady=(5, 2))

        status_info = load_status()
        is_act = status_info.get("is_active", True)
        init_text = "ACTIVO" if is_act else "INACTIVO"
        init_bg = ACCENT_GREEN if is_act else ACCENT_RED
        self.status_badge = tk.Label(self.sidebar, text=init_text, font=("Segoe UI", 10, "bold"), bg=init_bg, fg="#11111b", width=14, pady=3, bd=0)
        self.status_badge.pack(pady=3)

        self.last_run_lbl = tk.Label(self.sidebar, text="Último pedido:\nCargando...", fg=FG_TEXT, bg=BG_CARD, font=("Segoe UI", 8), justify="center")
        self.last_run_lbl.pack(pady=(5, 1))

        self.last_status_lbl = tk.Label(self.sidebar, text="Resultado: -", fg=FG_MUTED, bg=BG_CARD, font=("Segoe UI", 8))
        self.last_status_lbl.pack(pady=(0, 5))

        # --- Botones y Checkbox organizados de forma secuencial de arriba a abajo ---
        # Botón Toggle (Alternar Estado)
        self.toggle_btn = tk.Button(self.sidebar, text="Alternar Estado", font=("Segoe UI", 9, "bold"), bg=ACCENT, fg="#11111b", bd=0, pady=6, cursor="hand2", activeforeground="#11111b", command=self.toggle_bot_state)
        self.toggle_btn.pack(fill="x", padx=20, pady=4)

        # Botón Cancelar
        self.cancel_btn = tk.Button(self.sidebar, text="Cancelar Solicitud", font=("Segoe UI", 9, "bold"), bg=ACCENT_RED, fg="#11111b", bd=0, pady=6, cursor="hand2", activeforeground="#11111b", activebackground="#f3a8b8", command=self.confirm_cancel_lunch)
        self.cancel_btn.pack(fill="x", padx=20, pady=4)

        # Checkbox Cancelación
        self.cancelled_var = tk.BooleanVar(value=False)
        style = ttk.Style()
        style.configure("Dark.TCheckbutton", background=BG_CARD, foreground=FG_TEXT, font=("Segoe UI", 8))
        style.map("Dark.TCheckbutton", background=[("active", BG_CARD)], foreground=[("active", FG_TEXT)])
        
        self.cancelled_chk = ttk.Checkbutton(self.sidebar, text="Almuerzo Cancelado (Hoy)", style="Dark.TCheckbutton", variable=self.cancelled_var, command=self.toggle_cancelled_manually)
        self.cancelled_chk.pack(pady=4)

        # Información de Cancelaciones y Mantenimiento
        self.cancel_count_lbl = tk.Label(self.sidebar, text="Cancelaciones hoy: 0/3", fg=FG_MUTED, bg=BG_CARD, font=("Segoe UI", 8))
        self.cancel_count_lbl.pack(pady=1)

        self.cancel_date_lbl = tk.Label(self.sidebar, text="Cancelado el: N/A", fg=FG_MUTED, bg=BG_CARD, font=("Segoe UI", 8))
        self.cancel_date_lbl.pack(pady=1)

        self.refresh_cancellations_btn = tk.Button(self.sidebar, text="↻ Refrescar", font=("Segoe UI", 8), bg=BG_INPUT, fg=FG_TEXT, bd=0, pady=2, cursor="hand2", command=self.refresh_cancellations)
        self.refresh_cancellations_btn.pack(pady=4)

        # Botón Forzar Parada (siempre disponible, destacado en rojo)
        self.stop_processes_btn = tk.Button(self.sidebar, text="🚨 Forzar Parada", font=("Segoe UI", 9, "bold"), bg=ACCENT_RED, fg="#11111b", bd=0, pady=6, cursor="hand2", activeforeground="#11111b", activebackground="#f3a8b8", command=self.force_stop_active_processes)
        self.stop_processes_btn.pack(fill="x", padx=20, pady=(15, 4))

        # 2. Main Panel

        self.main_panel = tk.Frame(self.root, bg=BG_MAIN, padx=15, pady=15)
        self.main_panel.pack(side="right", fill="both", expand=True)

        self.notebook = ttk.Notebook(self.main_panel)
        self.notebook.pack(fill="both", expand=True)

        # Tab 1: Configuración
        self.tab_config = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_config, text="Configuración")
        self.create_config_tab()

        # Tab Cuestionario
        self.tab_questionnaire = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_questionnaire, text="Cuestionario")
        self.create_questionnaire_tab()

        # Tab 2: Logs
        self.tab_logs = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_logs, text="Consola de Logs")
        self.create_logs_tab()

        # Tab 3: Health Check
        self.tab_health = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_health, text="Salud & API")
        self.create_health_tab()

        # Tab 4: Manual de Uso
        self.tab_manual = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_manual, text="Manual de Uso")
        self.create_manual_tab()


    # --- Tab Configuración ---

    def create_config_tab(self):
        canvas = tk.Canvas(self.tab_config, bg=BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_config, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_MAIN)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Scroll con rueda del mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # --- Grupo 1: Credenciales de SiGCA ---
        group_sso = tk.LabelFrame(scrollable_frame, text=" Ajustes de Autenticación de SiGCA ", font=("Segoe UI", 10, "bold"), bg=BG_MAIN, fg=ACCENT, padx=15, pady=15, bd=1, highlightbackground=BG_INPUT)
        group_sso.pack(fill="x", pady=10, padx=5)

        tk.Label(group_sso, text="URL del Servicio:", bg=BG_MAIN, fg=FG_TEXT).grid(row=0, column=0, sticky="w", pady=6)
        self.url_ent = tk.Entry(group_sso, bg=BG_INPUT, fg=FG_TEXT, bd=0, width=50, insertbackground=FG_TEXT)
        self.url_ent.grid(row=0, column=1, columnspan=2, sticky="ew", pady=6, ipady=3)

        tk.Label(group_sso, text="Correo Corporativo:", bg=BG_MAIN, fg=FG_TEXT).grid(row=1, column=0, sticky="w", pady=6)
        self.user_ent = tk.Entry(group_sso, bg=BG_INPUT, fg=FG_TEXT, bd=0, width=50, insertbackground=FG_TEXT)
        self.user_ent.grid(row=1, column=1, columnspan=2, sticky="ew", pady=6, ipady=3)

        tk.Label(group_sso, text="Contraseña(s) (separadas por coma):", bg=BG_MAIN, fg=FG_TEXT).grid(row=2, column=0, sticky="w", pady=6)
        self.pass_ent = tk.Entry(group_sso, bg=BG_INPUT, fg=FG_TEXT, bd=0, show="*", width=42, insertbackground=FG_TEXT)
        self.pass_ent.grid(row=2, column=1, sticky="ew", pady=6, ipady=3)

        self.pass_visible = False
        self.eye_btn = tk.Button(group_sso, text="👁️", bg=BG_INPUT, fg=FG_TEXT, bd=0, width=4, cursor="hand2", activebackground=BG_INPUT, activeforeground=FG_TEXT, command=self.toggle_password_visibility)
        self.eye_btn.grid(row=2, column=2, sticky="e", padx=(5, 0), pady=6, ipady=1)
        group_sso.columnconfigure(1, weight=1)

        # --- Grupo 2: Telegram ---
        group_tg = tk.LabelFrame(scrollable_frame, text=" Configuración de Telegram (Alertas y Consultas) ", font=("Segoe UI", 10, "bold"), bg=BG_MAIN, fg=ACCENT, padx=15, pady=15, bd=1, highlightbackground=BG_INPUT)
        group_tg.pack(fill="x", pady=10, padx=5)

        tk.Label(group_tg, text="Telegram Bot Token:", bg=BG_MAIN, fg=FG_TEXT).grid(row=0, column=0, sticky="w", pady=6)
        self.tg_token_ent = tk.Entry(group_tg, bg=BG_INPUT, fg=FG_TEXT, bd=0, width=50, insertbackground=FG_TEXT)
        self.tg_token_ent.grid(row=0, column=1, columnspan=2, sticky="ew", pady=6, ipady=3)

        tk.Label(group_tg, text="Telegram Chat ID:", bg=BG_MAIN, fg=FG_TEXT).grid(row=1, column=0, sticky="w", pady=6)
        self.tg_chat_ent = tk.Entry(group_tg, bg=BG_INPUT, fg=FG_TEXT, bd=0, width=35, insertbackground=FG_TEXT)
        self.tg_chat_ent.grid(row=1, column=1, sticky="w", pady=6, ipady=3)

        self.tg_test_btn = tk.Button(group_tg, text="Probar Telegram", font=("Segoe UI", 9, "bold"), bg=ACCENT_BLUE, fg="#11111b", bd=0, cursor="hand2", activeforeground="#11111b", command=self.test_telegram_connection)
        self.tg_test_btn.grid(row=1, column=2, sticky="e", padx=(5, 0), pady=6, ipady=2)
        group_tg.columnconfigure(1, weight=1)

        # --- Grupo 3: Preferencias del Sistema ---
        group_pref = tk.LabelFrame(scrollable_frame, text=" Ajustes y Preferencias del Sistema ", font=("Segoe UI", 10, "bold"), bg=BG_MAIN, fg=ACCENT, padx=15, pady=15, bd=1, highlightbackground=BG_INPUT)
        group_pref.pack(fill="x", pady=10, padx=5)

        tk.Label(group_pref, text="Menú Favorito:", bg=BG_MAIN, fg=FG_TEXT).grid(row=0, column=0, sticky="w", pady=6)
        self.menu_cb = ttk.Combobox(group_pref, values=["Saludable", "Estándar"], state="readonly")
        self.menu_cb.grid(row=0, column=1, sticky="w", pady=6, ipady=2)

        tk.Label(group_pref, text="Revisión (Hora:Minuto):", bg=BG_MAIN, fg=FG_TEXT).grid(row=1, column=0, sticky="w", pady=6)
        self.hour_cb = ttk.Combobox(group_pref, values=[f"{i:02d}" for i in range(24)], width=5, state="readonly")
        self.hour_cb.grid(row=1, column=1, sticky="w", pady=6)
        self.min_cb = ttk.Combobox(group_pref, values=[f"{i:02d}" for i in range(60)], width=5, state="readonly")
        self.min_cb.grid(row=1, column=1, sticky="w", padx=(60, 0), pady=6)

        self.startup_var = tk.BooleanVar(value=False)
        self.startup_chk = tk.Checkbutton(group_pref, text="Iniciar automáticamente con Windows", variable=self.startup_var, bg=BG_MAIN, fg=FG_TEXT, activebackground=BG_MAIN, activeforeground=FG_TEXT, selectcolor=BG_INPUT, bd=0)
        self.startup_chk.grid(row=2, column=0, columnspan=2, sticky="w", pady=10)

        # --- Grupo 4: Programador de Tareas de Windows ---
        group_task = tk.LabelFrame(scrollable_frame, text=" Programador de Tareas de Windows ", font=("Segoe UI", 10, "bold"), bg=BG_MAIN, fg=ACCENT, padx=15, pady=15, bd=1, highlightbackground=BG_INPUT)
        group_task.pack(fill="x", pady=10, padx=5)

        task_desc = tk.Label(group_task, text="Registra una tarea diaria en el Programador de Tareas de Windows\npara que el bot se ejecute automáticamente a la hora configurada,\nincluso si la aplicación no está abierta.", bg=BG_MAIN, fg=FG_MUTED, font=("Segoe UI", 9), justify="left")
        task_desc.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Estado de la tarea
        self.task_status_lbl = tk.Label(group_task, text="Verificando...", bg=BG_MAIN, fg=FG_MUTED, font=("Segoe UI", 9, "bold"))
        self.task_status_lbl.grid(row=1, column=0, sticky="w", pady=6)

        # Botones
        self.register_task_btn = tk.Button(group_task, text="📋 Registrar Tarea Diaria", font=("Segoe UI", 9, "bold"), bg=ACCENT_GREEN, fg="#11111b", bd=0, padx=12, pady=5, cursor="hand2", activeforeground="#11111b", command=self.register_task_action)
        self.register_task_btn.grid(row=1, column=1, sticky="e", padx=(10, 5), pady=6)

        self.unregister_task_btn = tk.Button(group_task, text="🗑️ Eliminar Tarea", font=("Segoe UI", 9, "bold"), bg=ACCENT_RED, fg="#11111b", bd=0, padx=12, pady=5, cursor="hand2", activeforeground="#11111b", command=self.unregister_task_action)
        self.unregister_task_btn.grid(row=1, column=2, sticky="e", padx=(0, 0), pady=6)

        group_task.columnconfigure(0, weight=1)

        # Verificar estado inicial de la tarea (en hilo para no bloquear GUI)
        threading.Thread(target=self._refresh_task_status, daemon=True).start()

        # --- Loading indicator ---
        self.loading_lbl = tk.Label(scrollable_frame, text="", font=("Segoe UI", 10, "bold"), bg=BG_MAIN, fg=ACCENT_BLUE)
        self.loading_lbl.pack(pady=5)

        # --- Botonera Inferior ---
        btn_frame = tk.Frame(scrollable_frame, bg=BG_MAIN)
        btn_frame.pack(fill="x", pady=15, padx=5)

        self.save_btn = tk.Button(btn_frame, text="Guardar Configuración", font=("Segoe UI", 10, "bold"), bg=ACCENT_GREEN, fg="#11111b", bd=0, padx=15, pady=8, cursor="hand2", activeforeground="#11111b", command=self.save_settings)
        self.save_btn.pack(side="left")

        self.test_btn = tk.Button(btn_frame, text="Simular Pedido (Dry Run)", font=("Segoe UI", 10, "bold"), bg=ACCENT_YELLOW, fg="#11111b", bd=0, padx=15, pady=8, cursor="hand2", activeforeground="#11111b", command=self.run_dry_run_test)
        self.test_btn.pack(side="right")
        
        self.manual_btn = tk.Button(btn_frame, text="Solicitud Manual", font=("Segoe UI", 10, "bold"), bg=ACCENT_BLUE, fg="#11111b", bd=0, padx=15, pady=8, cursor="hand2", activeforeground="#11111b", command=self.run_manual_order)
        self.manual_btn.pack(side="right", padx=(0, 10))

    # --- Tab Cuestionario ---

    def create_questionnaire_tab(self):
        canvas = tk.Canvas(self.tab_questionnaire, bg=BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_questionnaire, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_MAIN)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Scroll con rueda del mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        header_frame = tk.Frame(scrollable_frame, bg=BG_CARD, padx=15, pady=15, bd=1, highlightbackground=BG_INPUT)
        header_frame.pack(fill="x", pady=10, padx=5)

        tk.Label(header_frame, text="Configuración del Formulario Adicional", font=("Segoe UI", 12, "bold"), bg=BG_CARD, fg=ACCENT).pack(anchor="w")
        tk.Label(header_frame, text="Modifica las respuestas predeterminadas que usará el bot al completar las encuestas diarias.", bg=BG_CARD, fg=FG_TEXT).pack(anchor="w", pady=(5,0))

        fields_frame = tk.Frame(scrollable_frame, bg=BG_MAIN)
        fields_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Ubicación
        tk.Label(fields_frame, text="Ubicación (Sede):", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(10, 2), padx=5)
        ubicaciones = ["Sede ExCle", "CNE Plaza Venezuela", "CNE Plaza Caracas", "UBV", "Mariche III", "Vicepresidencia", "SAIME Torre ACO Las Mercedes", "Otro", "PDVSA La Campiña", "INTEVEP - Los Teques", "Mariche I", "Mariche II", "SAIME Principal", "PDVSA Venadria"]
        self.q_ubicacion_cb = ttk.Combobox(fields_frame, values=ubicaciones, state="readonly", width=40)
        self.q_ubicacion_cb.grid(row=0, column=1, sticky="w", pady=(10, 2), padx=5)

        # 1 a 5 Estrellas
        tk.Label(fields_frame, text="Evaluación (1 a 5 estrellas):", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=(10, 2), padx=5)
        self.q_estrellas_cb = ttk.Combobox(fields_frame, values=["1", "2", "3", "4", "5"], state="readonly", width=10)
        self.q_estrellas_cb.grid(row=1, column=1, sticky="w", pady=(10, 2), padx=5)

        # Bien cocidos
        tk.Label(fields_frame, text="¿Los alimentos estaban bien cocidos?:", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=(10, 2), padx=5)
        self.q_cocidos_ent = tk.Entry(fields_frame, bg=BG_INPUT, fg=FG_TEXT, insertbackground=FG_TEXT, bd=0, width=43)
        self.q_cocidos_ent.grid(row=2, column=1, sticky="w", pady=(10, 2), padx=5)

        # Porción acorde
        tk.Label(fields_frame, text="¿La porción estaba acorde?:", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=(10, 2), padx=5)
        self.q_porcion_ent = tk.Entry(fields_frame, bg=BG_INPUT, fg=FG_TEXT, insertbackground=FG_TEXT, bd=0, width=43)
        self.q_porcion_ent.grid(row=3, column=1, sticky="w", pady=(10, 2), padx=5)

        # Condimentación (solo lectura)
        tk.Label(fields_frame, text="Condimentación de la comida:", bg=BG_MAIN, fg=FG_MUTED, font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky="w", pady=(10, 2), padx=5)
        self.q_condimentacion_ent = tk.Entry(fields_frame, bg=BG_CARD, fg=FG_MUTED, insertbackground=FG_TEXT, bd=0, width=43, state="disabled")
        self.q_condimentacion_ent.grid(row=4, column=1, sticky="w", pady=(10, 2), padx=5)

        # Asistir tarde
        tk.Label(fields_frame, text="¿Asistirá después de la 01:30 pm?:", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky="w", pady=(10, 2), padx=5)
        self.q_asistir_cb = ttk.Combobox(fields_frame, values=["Sí", "No"], state="readonly", width=10)
        self.q_asistir_cb.grid(row=5, column=1, sticky="w", pady=(10, 2), padx=5)

        # Comentario
        tk.Label(fields_frame, text="Comentario acerca del plato:", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).grid(row=6, column=0, sticky="nw", pady=(10, 2), padx=5)
        self.q_comentario_txt = scrolledtext.ScrolledText(fields_frame, bg=BG_INPUT, fg=FG_TEXT, font=("Segoe UI", 9), insertbackground=FG_TEXT, bd=0, height=4, width=40)
        self.q_comentario_txt.grid(row=6, column=1, sticky="w", pady=(10, 2), padx=5)

        # Separador y botón de guardar
        sep = tk.Frame(scrollable_frame, height=1, bg=BG_INPUT)
        sep.pack(fill="x", pady=15, padx=5)

        btn_frame = tk.Frame(scrollable_frame, bg=BG_MAIN)
        btn_frame.pack(fill="x", pady=5, padx=5)
        
        self.save_q_btn = tk.Button(btn_frame, text="💾 Guardar Respuestas", font=("Segoe UI", 10, "bold"), bg=ACCENT_GREEN, fg="#11111b", bd=0, padx=15, pady=8, cursor="hand2", activeforeground="#11111b", command=self.save_questionnaire_settings)
        self.save_q_btn.pack(side="left")

    def save_questionnaire_settings(self):
        self.save_q_btn.configure(state="disabled")
        self.root.update_idletasks()
        
        config = load_config()
        if "questionnaire" not in config:
            config["questionnaire"] = {}
            
        config["questionnaire"]["ubicacion"] = self.q_ubicacion_cb.get()
        config["questionnaire"]["estrellas"] = self.q_estrellas_cb.get()
        config["questionnaire"]["bien_cocidos"] = self.q_cocidos_ent.get().strip()
        config["questionnaire"]["porcion_acorde"] = self.q_porcion_ent.get().strip()
        # Condimentacion no se guarda porque es read-only
        config["questionnaire"]["asistir_tarde"] = self.q_asistir_cb.get()
        config["questionnaire"]["comentario"] = self.q_comentario_txt.get("1.0", tk.END).strip()
        
        save_config(config)
        
        self.save_q_btn.configure(state="normal")
        logger.info("Cuestionario actualizado guardado en config.json.")
        show_custom_success("Cuestionario Guardado", "Las respuestas para el formulario adicional se han guardado correctamente.")

    # --- Tab Logs ---

    def create_logs_tab(self):
        self.log_text = scrolledtext.ScrolledText(self.tab_logs, bg="#11111b", fg=FG_TEXT, font=("Consolas", 10), insertbackground=FG_TEXT, bd=0, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text.tag_config("info", foreground=ACCENT_BLUE)
        self.log_text.tag_config("warning", foreground=ACCENT_YELLOW)
        self.log_text.tag_config("error", foreground=ACCENT_RED)
        self.log_text.tag_config("critical", foreground=ACCENT_RED, font=("Consolas", 10, "bold"))

    # --- Tab Health ---

    def create_health_tab(self):
        info_frame = tk.Frame(self.tab_health, bg=BG_CARD, padx=20, pady=20, bd=1, highlightbackground=BG_INPUT)
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(info_frame, text="Monitoreo de Salud del Bot", font=("Segoe UI", 14, "bold"), bg=BG_CARD, fg=ACCENT).pack(anchor="w", pady=(0, 10))
        tk.Label(info_frame, text="La aplicación expone un servidor HTTP local para verificar la salud y monitorear el estado.", bg=BG_CARD, fg=FG_TEXT, justify="left", wraplength=550).pack(anchor="w", pady=(0, 20))

        url_frame = tk.Frame(info_frame, bg=BG_INPUT, padx=15, pady=10)
        url_frame.pack(fill="x", pady=10)
        tk.Label(url_frame, text="URL del Health Check:", bg=BG_INPUT, fg=FG_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        health_url_lbl = tk.Label(url_frame, text="http://127.0.0.1:18293/health", bg=BG_INPUT, fg=ACCENT_GREEN, font=("Consolas", 11, "bold"), cursor="hand2")
        health_url_lbl.pack(anchor="w", pady=(5, 0))
        health_url_lbl.bind("<Button-1>", lambda e: subprocess.run(["cmd", "/c", "start", "http://127.0.0.1:18293/"]))

        dash_frame = tk.Frame(info_frame, bg=BG_INPUT, padx=15, pady=10)
        dash_frame.pack(fill="x", pady=10)
        tk.Label(dash_frame, text="Dashboard Visual (Clic para abrir en navegador):", bg=BG_INPUT, fg=FG_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        dash_url_lbl = tk.Label(dash_frame, text="http://127.0.0.1:18293/", bg=BG_INPUT, fg=ACCENT_BLUE, font=("Consolas", 11, "bold"), cursor="hand2")
        dash_url_lbl.pack(anchor="w", pady=(5, 0))
        dash_url_lbl.bind("<Button-1>", lambda e: subprocess.run(["cmd", "/c", "start", "http://127.0.0.1:18293/"]))

        actions_frame = tk.Frame(info_frame, bg=BG_CARD)
        actions_frame.pack(fill="x", pady=20)

        tk.Button(actions_frame, text="Abrir Directorio de Evidencias", font=("Segoe UI", 10, "bold"), bg=BG_INPUT, fg=FG_TEXT, bd=0, pady=8, padx=15, cursor="hand2", activebackground=BG_INPUT, activeforeground=FG_TEXT, command=self.open_evidence_folder).pack(side="left")
        tk.Button(actions_frame, text="Abrir Archivo de Logs (.log)", font=("Segoe UI", 10, "bold"), bg=BG_INPUT, fg=FG_TEXT, bd=0, pady=8, padx=15, cursor="hand2", activebackground=BG_INPUT, activeforeground=FG_TEXT, command=self.open_log_file).pack(side="right")

        cleanup_frame = tk.Frame(info_frame, bg=BG_CARD)
        cleanup_frame.pack(fill="x", pady=(0, 20))
        tk.Button(cleanup_frame, text="🧹 Limpiar Todos los Registros (Logs y Evidencias)", font=("Segoe UI", 10, "bold"), bg=ACCENT_RED, fg="#11111b", bd=0, pady=8, padx=15, cursor="hand2", activebackground="#f3a8b8", activeforeground="#11111b", command=self.run_manual_cleanup).pack(side="left", fill="x", expand=True)

    # --- Tab Manual de Uso ---

    def create_manual_tab(self):
        canvas = tk.Canvas(self.tab_manual, bg=BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_manual, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_MAIN)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Scroll con rueda del mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # --- Título Superior y Enlace a Documentación Extensa ---
        header_frame = tk.Frame(scrollable_frame, bg=BG_CARD, padx=15, pady=15, bd=1, highlightbackground=BG_INPUT)
        header_frame.pack(fill="x", pady=(0, 10), padx=5)

        tk.Label(header_frame, text="Manual de Configuración y Ayuda", font=("Segoe UI", 14, "bold"), bg=BG_CARD, fg=ACCENT).pack(anchor="w")
        tk.Label(header_frame, text="Esta sección te guía a través de las diferentes configuraciones del bot.\nPara ver una guía aún más extensa y detallada en tu navegador, haz clic en el siguiente enlace:", bg=BG_CARD, fg=FG_TEXT, justify="left").pack(anchor="w", pady=(5, 10))

        doc_btn = tk.Button(header_frame, text="🌐 Abrir Documentación Extensa (/manual)", font=("Segoe UI", 10, "bold"), bg=ACCENT_BLUE, fg="#11111b", bd=0, padx=15, pady=6, cursor="hand2", activeforeground="#11111b", command=lambda: subprocess.run(["cmd", "/c", "start", "http://127.0.0.1:18293/manual"]))
        doc_btn.pack(anchor="w")
        doc_btn.bind("<Enter>", lambda e: doc_btn.configure(bg="#74c7ec"))
        doc_btn.bind("<Leave>", lambda e: doc_btn.configure(bg=ACCENT_BLUE))

        # Almacén de referencias de imágenes para evitar garbage collection
        self.manual_img_refs = {}

        # Definir las secciones del manual
        sections = [
            {
                "title": "1. Panel de Control (Sidebar)",
                "desc": "El panel lateral izquierdo (Sidebar) te muestra el estado en tiempo real del servicio (ACTIVO / INACTIVO) y el resultado del último pedido. Además, contiene los botones de acción rápida:\n"
                        "• Alternar Estado: Pausa o reactiva el planificador diario.\n"
                        "• Cancelar Solicitud: Cancela el almuerzo solicitado del día actual (máximo 3 cancelaciones diarias para evitar bloqueos).\n"
                        "• Check de Cancelación: Muestra el estatus de cancelación y se reinicia de manera automática a la medianoche.",
                "image": "side_bar_panel_control.png"
            },
            {
                "title": "2. Ajustes de Autenticación de SiGCA",
                "desc": "Configura las credenciales necesarias para iniciar sesión en la intranet de SiGCA a través de Microsoft SSO:\n"
                        "• URL del Servicio: La dirección web del portal de solicitudes.\n"
                        "• Correo Corporativo: Tu dirección de correo de la empresa.\n"
                        "• Contraseña(s): Puedes ingresar varias contraseñas separadas por coma en caso de expiración o rotación del sistema corporativo. El bot probará secuencialmente cada una de ellas.",
                "image": "autenticacion_sigca.png"
            },
            {
                "title": "3. Configuración de Telegram (Alertas y Consultas)",
                "desc": "Permite al bot enviarte notificaciones directamente a tu chat personal de Telegram:\n"
                        "• Telegram Bot Token: El token secreto proporcionado por @BotFather.\n"
                        "• Telegram Chat ID: Tu identificador numérico de chat personal o grupal.\n"
                        "• Botón 'Probar Telegram': Envía un mensaje instantáneo para comprobar la comunicación.",
                "image": "telegram_config.png"
            },
            {
                "title": "4. Ajustes y Preferencias del Sistema",
                "desc": "Configura el comportamiento básico de la aplicación:\n"
                        "• Menú Favorito: Selecciona 'Saludable' o 'Estándar' como prioridad de almuerzo.\n"
                        "• Horario de Revisión: La hora exacta a la que deseas que el bot empiece a intentar solicitar el almuerzo diariamente.\n"
                        "• Iniciar con Windows: Registra el bot en el Registro de Windows del usuario para cargarlo automáticamente al encender el equipo.",
                "image": "ajustes_preferencias_sistemas.png"
            },
            {
                "title": "5. Programador de Tareas de Windows",
                "desc": "Permite registrar una tarea programada a nivel de sistema operativo:\n"
                        "• Botón 'Registrar Tarea Diaria': Registra una tarea programada con PowerShell (solicitando elevación UAC) para iniciar el bot a la hora establecida, incluso si la GUI está cerrada.\n"
                        "• Botón 'Eliminar Tarea': Remueve la tarea del sistema por completo de forma limpia.",
                "image": "programar_tareas_windows.png"
            },
            {
                "title": "6. Consola de Logs Integrada",
                "desc": "Una consola visual en tiempo real que refleja las operaciones internas del bot. Las líneas se colorean según la importancia del evento:\n"
                        "• Celeste (INFO): Operaciones cotidianas y de confirmación.\n"
                        "• Amarillo (WARNING): Advertencias leves o problemas temporales.\n"
                        "• Rojo (ERROR/CRITICAL): Errores fatales o problemas de red.",
                "image": "console_log_section.png"
            },
            {
                "title": "7. Monitoreo de Salud & API",
                "desc": "Muestra los detalles de integración con servicios externos y mantenimiento local:\n"
                        "• URL del Health Check: Endpoint en formato JSON para monitorización técnica remota.\n"
                        "• Dashboard Visual: Enlace web local (http://127.0.0.1:18293/) que carga los logs y la última evidencia fotográfica en tu navegador.\n"
                        "• Botones de Mantenimiento: Accesos directos para abrir la carpeta de evidencias físicas o limpiar registros viejos.",
                "image": "seccion_salud_api.png"
            },
            {
                "title": "8. Botones de Acción del Sistema",
                "desc": "Ubicados en la parte inferior de la pestaña de configuración, permiten realizar acciones inmediatas:\n"
                        "• Guardar Configuración: Guarda y actualiza las variables de entorno (.env y config.json) y recarga el bot.\n"
                        "• Simular Pedido (Dry Run): Navega e interactúa en el navegador con Playwright, pero no efectúa el clic final de confirmación del pedido. Sirve para validar credenciales.\n"
                        "• Solicitud Manual: Salta todas las validaciones de horario y ejecuta inmediatamente una orden real.",
                "image": "botones_del_sistema.png"
            }
        ]

        # Crear los widgets por sección
        for idx, sec in enumerate(sections):
            sec_frame = tk.LabelFrame(scrollable_frame, text=f" {sec['title']} ", font=("Segoe UI", 10, "bold"), bg=BG_MAIN, fg=ACCENT, padx=15, pady=15, bd=1, highlightbackground=BG_INPUT)
            sec_frame.pack(fill="x", pady=10, padx=5)

            # Texto descriptivo
            desc_lbl = tk.Label(sec_frame, text=sec['desc'], font=("Segoe UI", 9), fg=FG_TEXT, bg=BG_MAIN, justify="left", anchor="w", wraplength=700)
            desc_lbl.pack(fill="x", pady=(0, 10))

            # Imagen de soporte
            img_name = sec['image']
            img_path = get_asset_path(os.path.join("images_info", img_name))

            if os.path.exists(img_path):
                try:
                    img = Image.open(img_path)
                    photo = ImageTk.PhotoImage(img)
                    self.manual_img_refs[img_name] = photo # Evitar que sea basura

                    img_lbl = tk.Label(sec_frame, image=photo, bg=BG_MAIN)
                    img_lbl.pack(anchor="w", pady=5)
                except Exception as e:
                    logger.error(f"Error al cargar imagen del manual {img_name}: {e}")
                    err_lbl = tk.Label(sec_frame, text=f"⚠️ No se pudo renderizar la captura: {img_name}", font=("Segoe UI", 9, "italic"), fg=ACCENT_RED, bg=BG_MAIN)
                    err_lbl.pack(anchor="w", pady=5)
            else:
                err_lbl = tk.Label(sec_frame, text=f"⚠️ Captura ausente: {img_name} (Ruta: {img_path})", font=("Segoe UI", 9, "italic"), fg=ACCENT_YELLOW, bg=BG_MAIN)
                err_lbl.pack(anchor="w", pady=5)

    # ------------------------------------------------------------------
    # Acciones e Interacciones
    # ------------------------------------------------------------------


    def toggle_password_visibility(self):
        if self.pass_visible:
            self.pass_ent.configure(show="*")
            self.eye_btn.configure(text="👁️")
            self.pass_visible = False
        else:
            self.pass_ent.configure(show="")
            self.eye_btn.configure(text="🙈")
            self.pass_visible = True

    def toggle_bot_state(self):
        status_info = load_status()
        is_act = not status_info.get("is_active", True)
        status_info["is_active"] = is_act
        save_status(status_info)
        update_gui_status_badge()

        try:
            bot = LunchBot()
        except Exception as e:
            logger.error(f"Error al instanciar LunchBot al cambiar estado: {e}")
            return

        if is_act:
            config = load_config()
            start_hour = config.get("start_hour", 15)
            start_minute = config.get("start_minute", 30)

            today_str = datetime.now().strftime("%Y-%m-%d")
            already_ordered_today = status_info.get("last_successful_run") == today_str
            time_valid = bot.is_time_valid()

            if already_ordered_today:
                msg = f"El planificador ha sido activado. El almuerzo de hoy ya se pidió con éxito. Próxima comprobación: mañana a las {start_hour:02d}:{start_minute:02d}."
            elif not time_valid:
                msg = f"El planificador ha sido activado. Fuera del rango horario. Próxima comprobación automática: hoy a las {start_hour:02d}:{start_minute:02d}."
            else:
                msg = "El planificador ha sido activado. Iniciando de inmediato el intento de solicitud de almuerzo en segundo plano..."
                logger.info(msg)
                bot._notify_toast("Planificador de Almuerzo", msg)
                bot._notify_telegram(f"🤖 <b>SiGCA Bot</b>:\n{html.escape(msg)}")
                threading.Thread(target=run_lunch_automation_job, kwargs={"dry_run": False, "gui_update_callback": update_gui_status_badge}, daemon=True).start()
                return

            logger.info(msg)
            bot._notify_toast("Planificador de Almuerzo", msg)
            bot._notify_telegram(f"🤖 <b>SiGCA Bot</b>:\n{html.escape(msg)}")
        else:
            msg = "El planificador ha sido desactivado (pausado) por el usuario."
            logger.info(msg)
            bot._notify_toast("Planificador de Almuerzo", msg)
            bot._notify_telegram(f"🤖 <b>SiGCA Bot</b>:\n{html.escape(msg)}")

    def load_settings_into_inputs(self):
        env = load_env_dict()
        self.url_ent.insert(0, env.get("SIGCA_URL", "https://sigca.ex-cle.com/"))
        self.user_ent.insert(0, env.get("SIGCA_USER", ""))
        self.pass_ent.insert(0, env.get("SIGCA_PASSWORDS", ""))
        self.tg_token_ent.insert(0, env.get("TELEGRAM_TOKEN", ""))
        self.tg_chat_ent.insert(0, env.get("TELEGRAM_CHAT_ID", ""))

        config = load_config()
        self.menu_cb.set(config.get("prefer_menu", "saludable").capitalize())
        self.hour_cb.set(f"{config.get('start_hour', 15):02d}")
        self.min_cb.set(f"{config.get('start_minute', 30):02d}")

        status = load_status()
        self.startup_var.set(status.get("startup_on_boot", False))
        self.cancelled_var.set(status.get("is_cancelled_today", False))

        # Cargar cuestionario
        q_config = config.get("questionnaire", {})
        self.q_ubicacion_cb.set(q_config.get("ubicacion", "Sede ExCle"))
        self.q_estrellas_cb.set(q_config.get("estrellas", "3"))
        
        self.q_cocidos_ent.delete(0, tk.END)
        self.q_cocidos_ent.insert(0, q_config.get("bien_cocidos", "last"))
        
        self.q_porcion_ent.delete(0, tk.END)
        self.q_porcion_ent.insert(0, q_config.get("porcion_acorde", "last"))
        
        self.q_condimentacion_ent.configure(state="normal")
        self.q_condimentacion_ent.delete(0, tk.END)
        self.q_condimentacion_ent.insert(0, str(q_config.get("condimentacion", 1)))
        self.q_condimentacion_ent.configure(state="disabled")
        
        self.q_asistir_cb.set(q_config.get("asistir_tarde", "Sí"))
        
        self.q_comentario_txt.delete("1.0", tk.END)
        self.q_comentario_txt.insert(tk.END, q_config.get("comentario", "Favor quitar el jugo de melon y las porciones no tienen suficiente proteina, quedando uno con hambre"))

    def show_loading(self, text):
        self.loading_lbl.configure(text=text)
        for btn in [self.save_btn, self.test_btn, self.manual_btn, self.tg_test_btn, self.cancel_btn, self.toggle_btn, self.refresh_cancellations_btn]:
            btn.configure(state="disabled")
        self.cancelled_chk.configure(state="disabled")
        self.root.update_idletasks()

    def hide_loading(self):
        self.loading_lbl.configure(text="")
        for btn in [self.save_btn, self.test_btn, self.manual_btn, self.tg_test_btn, self.cancel_btn, self.toggle_btn, self.refresh_cancellations_btn]:
            btn.configure(state="normal")
        self.cancelled_chk.configure(state="normal")
        self.root.update_idletasks()

    def save_settings(self):
        self.show_loading("Guardando configuración y actualizando ficheros...")

        url = self.url_ent.get().strip()
        user = self.user_ent.get().strip()
        passwords = self.pass_ent.get().strip()
        tg_token = self.tg_token_ent.get().strip()
        tg_chat = self.tg_chat_ent.get().strip()

        if not url or not user or not passwords:
            self.hide_loading()
            show_custom_error("Campos Incompletos", "Por favor completa la URL, el correo corporativo y al menos una contraseña.")
            logger.error("Error al guardar: faltan campos obligatorios de SiGCA.")
            return

        save_env_values({
            "SIGCA_URL": url,
            "SIGCA_USER": user,
            "SIGCA_PASSWORDS": passwords,
            "TELEGRAM_TOKEN": tg_token,
            "TELEGRAM_CHAT_ID": tg_chat
        })

        config = load_config()
        config["prefer_menu"] = self.menu_cb.get().lower()
        config["start_hour"] = int(self.hour_cb.get())
        config["start_minute"] = int(self.min_cb.get())
        save_config(config)

        startup_enabled = self.startup_var.get()
        set_startup(startup_enabled)

        status_info = load_status()
        status_info["startup_on_boot"] = startup_enabled
        save_status(status_info)

        self.root.after(1000, self._finish_save)

    def _finish_save(self):
        self.hide_loading()
        logger.info("Configuraciones guardadas y actualizadas exitosamente.")
        show_custom_success("Configuración Guardada", "Los cambios han sido guardados con éxito y las variables de entorno recargadas.")

    def test_telegram_connection(self):
        token = self.tg_token_ent.get().strip()
        chat_id = self.tg_chat_ent.get().strip()
        if not token or not chat_id:
            show_custom_warning("Faltan Credenciales", "Por favor ingresa el Bot Token y el Chat ID de Telegram para realizar la prueba.")
            return

        self.show_loading("Enviando mensaje de prueba a Telegram...")

        def run_test():
            success = send_telegram_message(token, chat_id, "🤖 <b>SiGCA Bot</b>:\nPrueba de comunicación exitosa. La aplicación puede mandarte alertas aquí.")
            self.root.after(0, lambda: self._finish_telegram_test(success))

        threading.Thread(target=run_test, daemon=True).start()

    def _finish_telegram_test(self, success):
        self.hide_loading()
        if success:
            logger.info("Prueba de comunicación con Telegram exitosa.")
            show_custom_success("Prueba Exitosa", "¡Mensaje de prueba enviado exitosamente a tu canal de Telegram!")
        else:
            logger.error("Error al enviar mensaje de prueba a Telegram.")
            show_custom_error("Error de Envío", "No se pudo conectar con Telegram. Revisa el token, el Chat ID o la conexión a internet.")

    def run_dry_run_test(self):
        self.run_bot_subprocess(["--run-job", "--dry-run", "--force-time"], "dry_run", "Iniciando simulación del pedido en seco (Dry Run). Por favor espera...")

    def run_manual_order(self):
        if show_custom_confirm("Solicitud Manual", "¿Deseas forzar la ejecución del pedido AHORA MISMO?\n\nEsto ignorará cualquier cancelación previa que hayas hecho hoy."):
            self.run_bot_subprocess(["--run-job", "--force-time"], "manual", "Iniciando solicitud manual de almuerzo. Por favor espera...")

    def confirm_cancel_lunch(self):
        status_info = load_status()
        today_str = datetime.now().strftime("%Y-%m-%d")
        c_count = status_info.get("cancellations_count", 0)
        if status_info.get("last_cancellation_date") != today_str:
            c_count = 0

        if c_count >= 3:
            show_custom_warning("Límite de Cancelaciones", "Has alcanzado el límite de 3 cancelaciones de almuerzo por día.")
            return

        if not show_custom_confirm("Confirmar Cancelación", f"¿Estás seguro de que deseas cancelar tu solicitud de almuerzo?\n\nLímite diario: 3 cancelaciones\nLlevas: {c_count}/3 cancelaciones hoy."):
            return

        self.run_bot_subprocess(["--cancel-order"], "cancel", "Cancelando solicitud de almuerzo... Por favor espera...")

    def run_manual_cleanup(self):
        if show_custom_confirm("Limpiar Registros", "¿Estás seguro de que deseas eliminar permanentemente todas las evidencias y logs antiguos?\n\nEsta acción no se puede deshacer."):
            try:
                from src.cleanup import clean_all_logs_and_evidence
                deleted = clean_all_logs_and_evidence()
                messagebox.showinfo("Limpieza Completada", f"Se han eliminado {deleted} archivos antiguos con éxito.")
            except Exception as e:
                logger.error(f"Error en limpieza manual: {e}")
                messagebox.showerror("Error", f"Ocurrió un error al intentar limpiar los registros:\n{e}")

    def toggle_cancelled_manually(self):
        val = self.cancelled_var.get()
        status_info = load_status()
        status_info["is_cancelled_today"] = val
        if val:
            status_info["last_cancellation_date"] = datetime.now().strftime("%Y-%m-%d")
        save_status(status_info)
        update_gui_status_badge()
        logger.info(f"Estado manual de cancelación modificado a: {val}")

    def refresh_cancellations(self):
        update_gui_status_badge()
        logger.info("Estado de cancelaciones refrescado en la GUI")

    # --- Acciones del Programador de Tareas de Windows ---

    def _refresh_task_status(self):
        """Verifica el estado de la tarea programada y actualiza la etiqueta."""
        exists = check_windows_task_exists()
        self.root.after(0, lambda: self._set_task_status_label(exists))

    def _set_task_status_label(self, exists):
        if exists:
            self.task_status_lbl.configure(text="✅ Tarea registrada en Windows", fg=ACCENT_GREEN)
        else:
            self.task_status_lbl.configure(text="⚠️ Sin tarea registrada", fg=ACCENT_YELLOW)

    def register_task_action(self):
        """Registra la tarea diaria en el Programador de Tareas de Windows."""
        hour = int(self.hour_cb.get())
        minute = int(self.min_cb.get())

        self.show_loading("Registrando tarea en el Programador de Windows (se solicitará permiso de Administrador)...")
        logger.info(f"Solicitando registro de tarea programada para las {hour:02d}:{minute:02d}...")

        def run_register():
            success, msg = register_windows_task(trigger_hour=hour, trigger_minute=minute)
            self.root.after(0, lambda: self._finish_task_action(success, msg))

        threading.Thread(target=run_register, daemon=True).start()

    def unregister_task_action(self):
        """Elimina la tarea diaria del Programador de Tareas de Windows."""
        self.show_loading("Eliminando tarea del Programador de Windows (se solicitará permiso de Administrador)...")
        logger.info("Solicitando eliminación de la tarea programada...")

        def run_unregister():
            success, msg = unregister_windows_task()
            self.root.after(0, lambda: self._finish_task_action(success, msg))

        threading.Thread(target=run_unregister, daemon=True).start()

    def _finish_task_action(self, success, msg):
        self.hide_loading()
        self._refresh_task_status()
        if success:
            show_custom_success("Operación Exitosa", msg)
        else:
            show_custom_error("Error de Operación", msg)

    # --- Utilidades ---

    def open_evidence_folder(self):
        folder = os.path.join(BASE_DIR, "evidence")
        os.makedirs(folder, exist_ok=True)
        subprocess.run(["explorer", folder])

    def open_log_file(self):
        log_file = os.path.join(BASE_DIR, "logs", "lunch_automation.log")
        if os.path.exists(log_file):
            subprocess.run(["notepad.exe", log_file])
        else:
            show_custom_info("Sin Logs", "El archivo de logs no existe aún.")

    # ---------------------------------------------------------------------------
    # Lógica de Diagnóstico y Subprocesos para Evitar Congelamientos
    # ---------------------------------------------------------------------------

    def verify_dependencies_startup(self):
        """Lanza la verificación de dependencias en un subproceso al iniciar."""
        logger.info("Iniciando verificación automática de dependencias...")
        
        import sys
        entry_script = sys.argv[0]
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, "--check-deps"]
        else:
            abs_script = os.path.abspath(entry_script)
            cmd = [sys.executable, abs_script, "--check-deps"]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combinar stderr en stdout para capturar todo
                text=True,
                encoding="utf-8",
                errors="backslashreplace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            # Monitorear el subproceso de chequeo en Tkinter
            self.root.after(500, lambda: self._poll_startup_check(proc, time.time()))
        except Exception as e:
            logger.error(f"Error al iniciar el subproceso de diagnóstico: {e}")

    def _poll_startup_check(self, proc, start_time):
        """Monitorea el subproceso de chequeo de dependencias."""
        ret_code = proc.poll()
        if ret_code is not None:
            # Leer toda la salida combinada (stdout + stderr ya combinados)
            all_output = ""
            try:
                all_output = proc.stdout.read().strip() if proc.stdout else ""
                proc.stdout.close()
            except Exception:
                pass

            if ret_code == 0 and "OK_PLAYWRIGHT" in all_output:
                logger.info("✅ Verificación de dependencias exitosa: Playwright y Chromium están listos y operativos.")
            else:
                logger.error(f"❌ Fallo en la verificación de dependencias: {all_output}")
                # Clasificar el error y decidir la acción
                self.root.after(0, lambda: self._handle_dep_check_failure(all_output))
            return

        # Verificar si excedió los 8 segundos (antivirus colgado o DLLs rotas)
        elapsed = time.time() - start_time
        if elapsed > 8:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.stdout.close()
            except Exception:
                pass
            kill_playwright_orphans()
            logger.critical("Timeout (8s) en la verificación de dependencias al inicio.")
            self.root.after(0, lambda: self._handle_dep_check_failure("TIMEOUT_8S"))
            return

        # Seguir monitoreando
        self.root.after(500, lambda: self._poll_startup_check(proc, start_time))

    def _handle_dep_check_failure(self, error_output):
        """Clasifica el error de dependencias y muestra un diálogo guiado al usuario."""
        error_lower = error_output.lower() if error_output else ""

        # Detectar si es un problema de navegador faltante
        is_browser_missing = any(kw in error_lower for kw in [
            "executable doesn't exist",
            "executable doesn\\'t exist",
            "browsertype.launch",
            "no such file",
            "not found",
            "error_playwright",
            "is not installed",
            "browser was not found",
        ])

        # Detectar si es un problema de timeout (DLLs o antivirus)
        is_timeout = "timeout_8s" in error_lower

        # Detectar si es un error de DLLs del sistema
        is_dll_error = any(kw in error_lower for kw in [
            "dll",
            "visual c++",
            "vcruntime",
            "msvcp",
            "status_dll_not_found",
            "0xc0000135",
        ])

        if is_timeout:
            # Timeout: probablemente DLLs faltantes o antivirus
            self._show_environment_repair_dialog(
                "⏱️ Verificación Colgada",
                "La prueba de arranque del navegador superó el tiempo límite (8 segundos) y fue abortada.\n\n"
                "Este síntoma ocurre cuando:\n"
                "• Faltan las librerías 'Microsoft Visual C++ Redistributable' en este Windows.\n"
                "• Un Antivirus o Windows Defender bloqueó silenciosamente el binario del navegador.\n\n"
                "¿Qué deseas hacer?",
                show_install_chromium=True,
                show_vcredist=True
            )
        elif is_dll_error:
            # Error explícito de DLLs
            self._show_environment_repair_dialog(
                "⚠️ Librerías del Sistema Faltantes",
                "El navegador de automatización no puede iniciarse porque faltan librerías del sistema (DLLs de C++).\n\n"
                "Necesitas instalar 'Microsoft Visual C++ Redistributable' para que SiGCABot funcione correctamente.\n\n"
                f"Detalle técnico:\n{error_output[:300]}",
                show_install_chromium=False,
                show_vcredist=True
            )
        elif is_browser_missing:
            # Navegador no instalado
            self._show_environment_repair_dialog(
                "🌐 Navegador No Encontrado",
                "SiGCABot necesita el navegador Chromium para funcionar, pero no lo encontró instalado en esta máquina.\n\n"
                "Pulsa 'Instalar Chromium' para descargarlo e instalarlo automáticamente.\n"
                "Esto requiere conexión a internet (~120 MB de descarga).",
                show_install_chromium=True,
                show_vcredist=False
            )
        else:
            # Error desconocido: ofrecer AMBAS opciones
            self._show_environment_repair_dialog(
                "❌ Error de Entorno",
                "La verificación automática del navegador falló.\n\n"
                "Esto puede deberse a:\n"
                "1. El navegador Chromium no está instalado en esta máquina.\n"
                "2. Faltan las librerías 'Microsoft Visual C++ Redistributable'.\n"
                "3. Tu Antivirus / Windows Defender bloqueó el navegador.\n\n"
                f"Detalle del error:\n{error_output[:300] if error_output else '(sin detalle disponible)'}\n\n"
                "Te recomendamos intentar instalar Chromium primero. Si el problema persiste, instala Visual C++ Redistributable.",
                show_install_chromium=True,
                show_vcredist=True
            )

    def _show_environment_repair_dialog(self, title, message, show_install_chromium=True, show_vcredist=True):
        """Muestra un diálogo premium con botones de acción para reparar el entorno."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg=BG_CARD)
        dialog.resizable(False, False)
        dialog.transient(self.root)

        # Tamaño y centrado
        dialog_w, dialog_h = 520, 420
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog_w // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog_h // 2)
        dialog.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")

        # Borde exterior de advertencia
        dialog.configure(highlightbackground=ACCENT_YELLOW, highlightthickness=2)

        # Marco interior
        inner = tk.Frame(dialog, bg=BG_CARD, padx=20, pady=15)
        inner.pack(fill=tk.BOTH, expand=True)

        # Icono y título
        header = tk.Frame(inner, bg=BG_CARD)
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header, text="⚠️", font=("Segoe UI Emoji", 28), bg=BG_CARD, fg=ACCENT_YELLOW).pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(header, text=title, font=("Segoe UI", 13, "bold"), bg=BG_CARD, fg=FG_TEXT, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Mensaje descriptivo con scroll
        msg_frame = tk.Frame(inner, bg=BG_INPUT, highlightbackground=FG_MUTED, highlightthickness=1)
        msg_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        msg_text = tk.Text(msg_frame, wrap=tk.WORD, bg=BG_INPUT, fg=FG_TEXT, font=("Segoe UI", 10),
                           relief=tk.FLAT, padx=10, pady=8, height=8, borderwidth=0)
        msg_text.insert("1.0", message)
        msg_text.configure(state=tk.DISABLED)
        msg_text.pack(fill=tk.BOTH, expand=True)

        # --- Botones de acción ---
        btn_frame = tk.Frame(inner, bg=BG_CARD)
        btn_frame.pack(fill=tk.X, pady=(0, 5))

        def make_btn(parent, text, color, command):
            btn = tk.Button(parent, text=text, font=("Segoe UI", 10, "bold"), bg=color, fg="#1e1e2e",
                            activebackground=color, activeforeground="#1e1e2e", relief=tk.FLAT,
                            cursor="hand2", padx=12, pady=6, command=command)
            btn.pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
            # Hover
            btn.bind("<Enter>", lambda e: btn.configure(bg=FG_TEXT, fg=BG_MAIN))
            btn.bind("<Leave>", lambda e: btn.configure(bg=color, fg="#1e1e2e"))
            return btn

        if show_install_chromium:
            make_btn(btn_frame, "⬇️ Instalar Chromium", ACCENT_GREEN, lambda: [dialog.destroy(), self.install_playwright_chromium_gui()])

        if show_vcredist:
            make_btn(btn_frame, "📦 Descargar C++ Redist.", ACCENT_BLUE, lambda: [dialog.destroy(), self._open_vcredist_download()])

        # Botón cerrar
        close_frame = tk.Frame(inner, bg=BG_CARD)
        close_frame.pack(fill=tk.X, pady=(5, 0))
        make_btn(close_frame, "Cerrar", FG_MUTED, dialog.destroy)

        dialog.grab_set()
        dialog.focus_force()

    def _open_vcredist_download(self):
        """Abre la página de descarga de Microsoft Visual C++ Redistributable y muestra instrucciones."""
        import webbrowser
        url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
        logger.info(f"Abriendo enlace de descarga de Visual C++ Redistributable: {url}")
        webbrowser.open(url)
        show_custom_info(
            "Instrucciones de Instalación",
            "Se ha abierto la descarga de 'Microsoft Visual C++ Redistributable' en tu navegador.\n\n"
            "Pasos a seguir:\n"
            "1. Ejecuta el archivo 'vc_redist.x64.exe' que se descargó.\n"
            "2. Acepta los términos y haz clic en 'Instalar'.\n"
            "3. Reinicia SiGCABot después de la instalación.\n\n"
            "Si tu Windows es de 32 bits (poco probable), descarga la versión x86 desde la página de Microsoft."
        )

    def install_playwright_chromium_gui(self):
        """Descarga e instala Chromium mostrando pantalla de carga."""
        self.show_loading("Descargando e instalando el navegador Chromium. Por favor espera...")
        logger.info("Iniciando instalador automático de Chromium de Playwright...")

        def run_install():
            try:
                # Localizar el driver ejecutable interno de playwright
                from playwright._impl._driver import compute_driver_executable
                driver_executable, driver_cli = compute_driver_executable()
                cmd = [driver_executable, driver_cli, "install", "chromium"]
            except Exception as e:
                # Comportamiento alternativo
                cmd = [sys.executable, "-m", "playwright", "install", "chromium"]

            logger.info(f"Ejecutando instalador: {' '.join(cmd)}")
            try:
                # Asegurar que PLAYWRIGHT_BROWSERS_PATH apunte al directorio global del usuario
                env = os.environ.copy()
                env["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
                    os.path.expanduser("~"), "AppData", "Local", "ms-playwright"
                )

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # Leer y loguear el progreso en tiempo real
                for line in iter(proc.stdout.readline, ""):
                    msg = line.strip()
                    if msg:
                        self.root.after(0, lambda m=msg: logger.info(m))
                proc.stdout.close()
                ret_code = proc.wait()
                
                if ret_code == 0:
                    self.root.after(0, lambda: self._finish_installation(True, "Navegador Chromium instalado exitosamente."))
                else:
                    self.root.after(0, lambda: self._finish_installation(False, f"La instalación falló con código {ret_code}."))
            except Exception as ex:
                self.root.after(0, lambda: self._finish_installation(False, f"Excepción durante la instalación: {ex}"))

        threading.Thread(target=run_install, daemon=True).start()

    def _finish_installation(self, success, message):
        self.hide_loading()
        if success:
            logger.info(message)
            show_custom_success(
                "Instalación Exitosa",
                "✅ Chromium se ha instalado correctamente.\n\n"
                "Ya puedes usar los botones de 'Simular Pedido', 'Solicitud Manual' y 'Cancelar Solicitud'.\n\n"
                "Te recomendamos hacer una prueba con 'Simular Pedido (Dry Run)' para verificar que todo funcione."
            )
        else:
            logger.error(message)
            show_custom_error("Error de Instalación", f"No se pudo completar la instalación automática de Chromium:\n\n{message}")

    def run_bot_subprocess(self, args_list, operation_type, loading_text):
        """Lanza el bot en un subproceso seguro fuera del hilo de la GUI."""
        if self.active_subprocess is not None:
            show_custom_error("Proceso en Curso", "Ya existe una operación de automatización en ejecución. Espera a que termine o usa 'Forzar Parada'.")
            return

        self.show_loading(loading_text)
        self.subprocess_type = operation_type
        self.subprocess_start_time = time.time()
        self.subprocess_output_lines = []

        import sys
        entry_script = sys.argv[0]
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable] + args_list
        else:
            abs_script = os.path.abspath(entry_script)
            cmd = [sys.executable, abs_script] + args_list

        logger.info(f"Iniciando subproceso para {operation_type}: {' '.join(cmd)}")

        try:
            self.active_subprocess = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="backslashreplace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Hilo para leer la salida estándar en tiempo real
            def read_stdout():
                proc = self.active_subprocess
                if proc and proc.stdout:
                    for line in iter(proc.stdout.readline, ""):
                        msg = line.strip()
                        if msg:
                            self.subprocess_output_lines.append(msg)
                            self.root.after(0, lambda m=msg: logger.info(m))
                    proc.stdout.close()

            threading.Thread(target=read_stdout, daemon=True).start()

            # Comenzar el bucle de sondeo (polling) en Tkinter
            self.root.after(500, self._poll_subprocess)

        except Exception as e:
            logger.error(f"Error al iniciar el subproceso: {e}")
            self._finish_subprocess(5, f"No se pudo iniciar el subproceso: {e}")

    def _poll_subprocess(self):
        """Sondea el estado del subproceso y maneja el timeout de 30s."""
        proc = self.active_subprocess
        if proc is None:
            return

        # Verificar si el proceso ha terminado
        ret_code = proc.poll()
        if ret_code is not None:
            self._finish_subprocess(ret_code, f"El proceso terminó con código {ret_code}")
            return

        # Verificar si se superó el tiempo límite (30 segundos)
        elapsed = time.time() - self.subprocess_start_time
        if elapsed > 30:
            logger.warning(f"Límite de tiempo excedido (30s) para la operación: {self.subprocess_type}. Forzando detención...")
            self._terminate_active_subprocess(timed_out=True)
            return

        # Continuar sondeando cada 500ms
        self.root.after(500, self._poll_subprocess)

    def _finish_subprocess(self, exit_code, detail_msg):
        """Finaliza el estado de la GUI e informa al usuario sobre el resultado del subproceso."""
        self.active_subprocess = None
        op_type = self.subprocess_type
        self.subprocess_type = None
        self.hide_loading()
        update_gui_status_badge()

        # Encontrar el mensaje de completitud en la salida
        completion_msg = ""
        for line in reversed(self.subprocess_output_lines):
            # Intentar encontrar la línea final con el resultado
            if "completada" in line.lower() or "falló" in line.lower() or "error" in line.lower() or "éxito" in line.lower():
                completion_msg = line
                break
        if not completion_msg:
            completion_msg = detail_msg

        if op_type == "dry_run":
            if exit_code == 0:
                logger.info(f"Simulación Dry-Run completada con ÉXITO: {completion_msg}")
                show_custom_success("Dry-Run Exitoso", f"La prueba se completó correctamente:\n\n{completion_msg}\n\nCaptura guardada en evidences.")
            else:
                logger.error(f"Simulación Dry-Run FALLÓ (código {exit_code}): {completion_msg}")
                show_custom_error("Dry-Run Fallido", f"La simulación reportó un fallo:\n\n{completion_msg}")

        elif op_type == "manual":
            if exit_code == 0:
                logger.info(f"Solicitud manual completada con ÉXITO: {completion_msg}")
                show_custom_success("Solicitud Exitosa", f"El pedido manual se completó correctamente:\n\n{completion_msg}")
            else:
                logger.error(f"Solicitud manual FALLÓ (código {exit_code}): {completion_msg}")
                show_custom_error("Solicitud Fallida", f"El pedido manual reportó un fallo:\n\n{completion_msg}")

        elif op_type == "cancel":
            if exit_code == 0:
                logger.info(f"Cancelación completada con ÉXITO: {completion_msg}")
                show_custom_success("Cancelación Exitosa", f"La cancelación se completó correctamente:\n\n{completion_msg}")
            else:
                logger.error(f"Cancelación FALLÓ (código {exit_code}): {completion_msg}")
                show_custom_error("Cancelación Fallida", f"La cancelación reportó un fallo:\n\n{completion_msg}")

    def _terminate_active_subprocess(self, timed_out=False):
        """Detiene de forma forzada el subproceso activo y limpia huérfanos."""
        proc = self.active_subprocess
        if proc is None:
            return

        self.active_subprocess = None
        op_type = self.subprocess_type
        self.subprocess_type = None

        # Terminar el proceso
        try:
            proc.kill()
            logger.info("Subproceso de automatización terminado de forma forzada.")
        except Exception as e:
            logger.warning(f"No se pudo matar el subproceso directamente: {e}")

        # Limpiar procesos huérfanos de playwright (Chromium, node)
        kill_playwright_orphans()

        # Registrar el error
        err_msg = f"La operación '{op_type}' fue detenida " + ("automáticamente por límite de tiempo (30s)." if timed_out else "manualmente por el usuario.")
        logger.error(err_msg)

        # Enviar notificación a Telegram si está configurado
        self._notify_telegram_timeout(op_type, timed_out)

        # Reactivar la interfaz
        self.hide_loading()
        update_gui_status_badge()

        # Mostrar aviso de error
        show_custom_error("Operación Cancelada", err_msg)

    def _notify_telegram_timeout(self, op_type, timed_out):
        """Envía de forma asíncrona una alerta de timeout a Telegram."""
        try:
            from src.config import load_env_dict
            env = load_env_dict()
            token = env.get("TELEGRAM_TOKEN")
            chat_id = env.get("TELEGRAM_CHAT_ID")
            if token and chat_id:
                reason = "límite de tiempo excedido (30s)" if timed_out else "cancelación manual del usuario"
                msg = f"🚨 <b>Alerta de SiGCABot</b>:\nLa operación <code>{op_type}</code> fue interrumpida debido a: {reason}."
                # Ejecutar asíncronamente en un hilo
                threading.Thread(
                    target=send_telegram_message,
                    args=(token, chat_id, msg),
                    daemon=True
                ).start()
        except Exception as e:
            logger.debug(f"No se pudo enviar notificación de timeout a Telegram: {e}")

    def force_stop_active_processes(self):
        """Acción del botón de parada forzada en el sidebar."""
        if self.active_subprocess is None:
            # Si no hay un subproceso registrado, limpiar huérfanos de todos modos por seguridad
            logger.info("No hay ningún subproceso activo en la GUI. Limpiando procesos de Playwright huérfanos...")
            kill_playwright_orphans()
            show_custom_success("Limpieza Completada", "Se limpiaron todos los procesos huérfanos de Chromium/Node del sistema.")
            return

        if show_custom_confirm("Forzar Parada", "¿Estás seguro de que deseas detener inmediatamente la automatización activa?"):
            logger.info("Deteniendo proceso activo a petición del usuario...")
            self._terminate_active_subprocess(timed_out=False)

    # --- Bandeja del Sistema (System Tray) ---

    def minimize_to_tray(self):
        self.root.withdraw()
        logger.info("Aplicación minimizada a la bandeja del sistema.")
        global tray_icon
        if not tray_icon:
            self.create_tray_icon()

    def create_tray_icon(self):
        global tray_icon
        icon_path = get_asset_path("robot_hamburger_icon.png")
        try:
            img = Image.open(icon_path)
        except Exception:
            img = Image.new('RGB', (64, 64), color=(30, 30, 56))

        menu = pystray.Menu(
            pystray.MenuItem("Abrir Panel", self.restore_from_tray, default=True),
            pystray.MenuItem("Ejecutar Ahora (Simulación)", lambda: threading.Thread(
                target=run_lunch_automation_job,
                kwargs={"dry_run": True, "gui_update_callback": update_gui_status_badge},
                daemon=True
            ).start()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", self.exit_application)
        )

        tray_icon = pystray.Icon("SiGCABot", img, "SiGCA Lunch Bot", menu)
        threading.Thread(target=tray_icon.run, daemon=True).start()

    def restore_from_tray(self):
        self.root.deiconify()
        self.root.focus_force()

    def exit_application(self):
        global tray_icon
        state.stop_threads = True
        logger.info("Cerrando todos los servicios y saliendo de la aplicación...")
        if tray_icon:
            tray_icon.stop()
        self.root.destroy()
        sys.exit(0)


# ---------------------------------------------------------------------------
# Punto de Entrada Principal (Modo GUI)
# ---------------------------------------------------------------------------

def main():
    # Levantar servicios en hilos secundarios
    threading.Thread(target=start_http_server, daemon=True).start()
    threading.Thread(target=start_telegram_poller, daemon=True).start()
    threading.Thread(target=start_scheduler, kwargs={"gui_update_callback": update_gui_status_badge}, daemon=True).start()

    # Levantar GUI
    root = tk.Tk()

    icon_path = get_asset_path("robot_hamburger_icon.png")
    if os.path.exists(icon_path):
        try:
            img = Image.open(icon_path)
            photo = ImageTk.PhotoImage(img)
            root.iconphoto(True, photo)
            root._icon_image = photo
        except Exception as e:
            logger.error(f"Error al establecer el icono de la ventana: {e}")

    AppGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
