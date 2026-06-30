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
    return parser.parse_args()


_args = _parse_args()

# ---------------------------------------------------------------------------
# Modo CLI (--run-job o --cancel-order): Sin GUI, solo ejecución directa
# ---------------------------------------------------------------------------

if _args.run_job or _args.cancel_order:
    # Importar módulos de infraestructura
    from src.config import BASE_DIR
    from src.logger import logger
    from src.bot_engine import LunchBot

    if _args.run_job:
        logger.info("Iniciando ejecución de LunchBot en modo CLI (--run-job)...")
        try:
            bot = LunchBot()
            if _args.force_time:
                bot.is_time_valid = lambda *a, **k: True
                logger.info("Validación horaria forzada (desactivada).")
            exit_code, msg, evidence = bot.run_automation(dry_run=_args.dry_run)
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
from src.bot_engine import LunchBot
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
    """Inserta una línea de log en el widget ScrolledText de la consola."""
    if app and app.log_text:
        app.log_text.configure(state="normal")
        tag = level.lower()
        app.log_text.insert("end", msg + "\n", tag)
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
        self.wait_window()

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
        PremiumMessageBox(app.root, title, message, "info")
    else:
        messagebox.showinfo(title, message)

def show_custom_success(title, message):
    if app and app.root:
        PremiumMessageBox(app.root, title, message, "success")
    else:
        messagebox.showinfo(title, message)

def show_custom_error(title, message):
    if app and app.root:
        PremiumMessageBox(app.root, title, message, "error")
    else:
        messagebox.showerror(title, message)

def show_custom_warning(title, message):
    if app and app.root:
        PremiumMessageBox(app.root, title, message, "warning")
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
        self.wait_window()

    def on_yes(self):
        self.result = True
        self.destroy()

    def on_no(self):
        self.result = False
        self.destroy()

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
        self.root.geometry("1000x800")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(False, True)
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        self.setup_styles()
        self.create_layout()
        self.load_settings_into_inputs()
        update_gui_status_badge()

        # Conectar el handler de logs a la GUI
        gui_log_handler.connect(self.log_text, append_log_gui)

        logger.info("Aplicación iniciada. Bienvenido al panel de SiGCA Bot.")

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

        # Imagen de Bender
        img_path = get_asset_path("bender_chef.png")
        if os.path.exists(img_path):
            try:
                raw_img = Image.open(img_path)
                resized = raw_img.resize((200, 200), Image.Resampling.LANCZOS)
                self.bender_img = ImageTk.PhotoImage(resized)
                img_lbl = tk.Label(self.sidebar, image=self.bender_img, bg=BG_CARD)
                img_lbl.pack(pady=20)
            except Exception as e:
                logger.error(f"Error cargando imagen bender: {e}")
        else:
            lbl = tk.Label(self.sidebar, text="🤖 LunchBot", fg=ACCENT, bg=BG_CARD, font=("Segoe UI", 20, "bold"))
            lbl.pack(pady=40)

        title_lbl = tk.Label(self.sidebar, text="SiGCA Lunch Bot", fg=FG_TEXT, bg=BG_CARD, font=("Segoe UI", 14, "bold"))
        title_lbl.pack()

        version_lbl = tk.Label(self.sidebar, text="Versión 2.2.0", fg=FG_MUTED, bg=BG_CARD, font=("Segoe UI", 9))
        version_lbl.pack(pady=(0, 20))

        sep = tk.Frame(self.sidebar, height=1, bg=BG_INPUT)
        sep.pack(fill="x", padx=20, pady=10)

        # Badge de Estado
        state_title = tk.Label(self.sidebar, text="ESTADO DEL SERVICIO", fg=FG_MUTED, bg=BG_CARD, font=("Segoe UI", 8, "bold"))
        state_title.pack(pady=(10, 5))

        status_info = load_status()
        is_act = status_info.get("is_active", True)
        init_text = "ACTIVO" if is_act else "INACTIVO"
        init_bg = ACCENT_GREEN if is_act else ACCENT_RED
        self.status_badge = tk.Label(self.sidebar, text=init_text, font=("Segoe UI", 11, "bold"), bg=init_bg, fg="#11111b", width=16, pady=4, bd=0)
        self.status_badge.pack(pady=5)

        self.last_run_lbl = tk.Label(self.sidebar, text="Último pedido:\nCargando...", fg=FG_TEXT, bg=BG_CARD, font=("Segoe UI", 9), justify="center")
        self.last_run_lbl.pack(pady=(15, 2))

        self.last_status_lbl = tk.Label(self.sidebar, text="Resultado: -", fg=FG_MUTED, bg=BG_CARD, font=("Segoe UI", 8))
        self.last_status_lbl.pack(pady=(0, 20))

        # Botón Toggle
        self.toggle_btn = tk.Button(self.sidebar, text="Alternar Estado", font=("Segoe UI", 10, "bold"), bg=ACCENT, fg="#11111b", bd=0, pady=8, cursor="hand2", activeforeground="#11111b", command=self.toggle_bot_state)
        self.toggle_btn.pack(fill="x", padx=20, side="bottom", pady=(10, 20))

        # Botón Cancelar
        self.cancel_btn = tk.Button(self.sidebar, text="Cancelar Solicitud", font=("Segoe UI", 10, "bold"), bg=ACCENT_RED, fg="#11111b", bd=0, pady=8, cursor="hand2", activeforeground="#11111b", activebackground="#f3a8b8", command=self.confirm_cancel_lunch)
        self.cancel_btn.pack(fill="x", padx=20, side="bottom", pady=(10, 0))

        self.cancel_count_lbl = tk.Label(self.sidebar, text="Cancelaciones hoy: 0/3", fg=FG_MUTED, bg=BG_CARD, font=("Segoe UI", 8))
        self.cancel_count_lbl.pack(side="bottom", pady=(5, 0))

        self.refresh_cancellations_btn = tk.Button(self.sidebar, text="↻ Refrescar", font=("Segoe UI", 8), bg=BG_INPUT, fg=FG_TEXT, bd=0, pady=2, cursor="hand2", command=self.refresh_cancellations)
        self.refresh_cancellations_btn.pack(side="bottom", pady=(5, 0))
        
        self.cancel_date_lbl = tk.Label(self.sidebar, text="Cancelado el: N/A", fg=FG_MUTED, bg=BG_CARD, font=("Segoe UI", 8))
        self.cancel_date_lbl.pack(side="bottom")

        self.cancelled_var = tk.BooleanVar(value=False)
        
        style = ttk.Style()
        style.configure("Dark.TCheckbutton", background=BG_CARD, foreground=FG_TEXT, font=("Segoe UI", 8))
        style.map("Dark.TCheckbutton", background=[("active", BG_CARD)], foreground=[("active", FG_TEXT)])
        
        self.cancelled_chk = ttk.Checkbutton(self.sidebar, text="Almuerzo Cancelado (Hoy)", style="Dark.TCheckbutton", variable=self.cancelled_var, command=self.toggle_cancelled_manually)
        self.cancelled_chk.pack(side="bottom", pady=(10, 0))


        # 2. Main Panel
        self.main_panel = tk.Frame(self.root, bg=BG_MAIN, padx=15, pady=15)
        self.main_panel.pack(side="right", fill="both", expand=True)

        self.notebook = ttk.Notebook(self.main_panel)
        self.notebook.pack(fill="both", expand=True)

        # Tab 1: Configuración
        self.tab_config = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_config, text="Configuración")
        self.create_config_tab()

        # Tab 2: Logs
        self.tab_logs = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_logs, text="Consola de Logs")
        self.create_logs_tab()

        # Tab 3: Health Check
        self.tab_health = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_health, text="Salud & API")
        self.create_health_tab()

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
        self.show_loading("Iniciando simulación del pedido en seco (Dry Run). Por favor espera...")
        logger.info("Iniciando prueba manual Dry Run del bot de almuerzo...")

        def run_test_thread():
            try:
                bot = LunchBot()
                bot.is_time_valid = lambda *args, **kwargs: True
                exit_code, msg, evidence = bot.run_automation(dry_run=True)
                self.root.after(0, lambda: self._finish_dry_run(exit_code, msg, evidence))
            except Exception as e:
                self.root.after(0, lambda: self._finish_dry_run(5, f"Excepción crítica durante la prueba: {e}", None))

        threading.Thread(target=run_test_thread, daemon=True).start()

    def _finish_dry_run(self, exit_code, msg, evidence):
        self.hide_loading()
        if exit_code == 0:
            logger.info(f"Simulación Dry-Run completada con ÉXITO: {msg}")
            show_custom_success("Dry-Run Exitoso", f"La prueba se completó correctamente:\n\n{msg}\n\nCaptura guardada en evidences.")
        else:
            logger.error(f"Simulación Dry-Run FALLÓ (código {exit_code}): {msg}")
            show_custom_error("Dry-Run Fallido", f"La simulación reportó un fallo:\n\n{msg}")

    def run_manual_order(self):
        self.show_loading("Iniciando solicitud manual de almuerzo. Por favor espera...")
        logger.info("Iniciando solicitud manual...")

        def run_manual_thread():
            try:
                bot = LunchBot()
                bot.is_time_valid = lambda *args, **kwargs: True
                exit_code, msg, evidence = bot.run_automation(dry_run=False, is_manual=True)
                self.root.after(0, lambda: self._finish_manual_order(exit_code, msg, evidence))
            except Exception as e:
                self.root.after(0, lambda: self._finish_manual_order(5, f"Excepción crítica durante la solicitud: {e}", None))

        threading.Thread(target=run_manual_thread, daemon=True).start()

    def _finish_manual_order(self, exit_code, msg, evidence):
        self.hide_loading()
        update_gui_status_badge()
        if exit_code == 0:
            logger.info(f"Solicitud manual completada con ÉXITO: {msg}")
            show_custom_success("Solicitud Exitosa", f"El pedido manual se completó correctamente:\n\n{msg}")
        else:
            logger.error(f"Solicitud manual FALLÓ (código {exit_code}): {msg}")
            show_custom_error("Solicitud Fallida", f"El pedido manual reportó un fallo:\n\n{msg}")


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

        self.show_loading("Cancelando solicitud de almuerzo... Por favor espera...")
        logger.info("Iniciando solicitud de cancelación del almuerzo...")

        def run_cancel_thread():
            try:
                bot = LunchBot()
                exit_code, msg, evidence = bot.cancel_lunch_order()
                self.root.after(0, lambda: self._finish_cancel_lunch(exit_code, msg, evidence))
            except Exception as e:
                self.root.after(0, lambda: self._finish_cancel_lunch(5, f"Excepción crítica durante la cancelación: {e}", None))

        threading.Thread(target=run_cancel_thread, daemon=True).start()

    def run_manual_order(self):
        if show_custom_confirm("Solicitud Manual", "¿Deseas forzar la ejecución del pedido AHORA MISMO?\n\nEsto ignorará cualquier cancelación previa que hayas hecho hoy."):
            threading.Thread(target=self._run_bot_manual_thread, daemon=True).start()

    def run_manual_cleanup(self):
        if show_custom_confirm("Limpiar Registros", "¿Estás seguro de que deseas eliminar permanentemente todas las evidencias y logs antiguos?\n\nEsta acción no se puede deshacer."):
            try:
                from src.cleanup import clean_all_logs_and_evidence
                deleted = clean_all_logs_and_evidence()
                messagebox.showinfo("Limpieza Completada", f"Se han eliminado {deleted} archivos antiguos con éxito.")
            except Exception as e:
                logger.error(f"Error en limpieza manual: {e}")
                messagebox.showerror("Error", f"Ocurrió un error al intentar limpiar los registros:\n{e}")

    def _finish_cancel_lunch(self, exit_code, msg, evidence):
        self.hide_loading()
        if exit_code == 0:
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
            update_gui_status_badge()

            try:
                bot = LunchBot()
                bot._notify_telegram(f"⚠️ <b>Advertencia de Cancelación</b>:\nSe ha cancelado la solicitud de almuerzo. Cancelaciones realizadas hoy: {c_count}/3.")
            except Exception:
                pass

            show_custom_warning("Solicitud Cancelada", f"La solicitud de almuerzo ha sido cancelada con éxito.\n\nContador de cancelaciones de hoy: {c_count}/3.\nAdvertencia: El límite es de 3 cancelaciones por día.")
        else:
            logger.error(f"Cancelación FALLÓ (código {exit_code}): {msg}")
            show_custom_error("Cancelación Fallida", f"Ocurrió un error al intentar cancelar:\n\n{msg}")

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
