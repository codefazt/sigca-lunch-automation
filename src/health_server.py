"""
Servidor HTTP local de Health Check para SiGCABot.
Expone endpoints para monitoreo de salud, dashboard visual y capturas de evidencia.

Endpoints:
    GET /        → Dashboard HTML con estado, logs recientes y última evidencia
    GET /health  → JSON con estado del bot para telemetría
    GET /evidence?name=<archivo>  → Sirve imagen de evidencia
"""

import os
import json
import logging
import http.server
import socketserver
import urllib.parse

from src.config import BASE_DIR, load_status
from src import state

logger = logging.getLogger("SiGCABot")


class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    """Manejador HTTP para el servidor de health check local."""

    def log_message(self, format, *args):
        pass  # Silenciar registros en consola de peticiones HTTP

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == "/health":
            self._handle_health()
        elif path == "/evidence":
            self._handle_evidence(parsed_path)
        elif path == "/images_info":
            self._handle_images_info(parsed_path)
        elif path == "/manual":
            self._handle_manual()
        elif path == "/":
            self._handle_dashboard()
        else:
            self.send_error(404, "Not Found")


    def _handle_health(self):
        """Endpoint JSON de telemetría."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        status_data = load_status()
        response = {
            "status": "ok",
            "active": status_data.get("is_active", True),
            "last_run": status_data.get("last_run_timestamp", "Nunca"),
            "last_status": status_data.get("last_run_status", "N/A"),
            "version": "2.2.0"
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def _handle_evidence(self, parsed_path):
        """Sirve una imagen de evidencia por nombre."""
        query = urllib.parse.parse_qs(parsed_path.query)
        filename = query.get("name", [None])[0]
        if filename:
            filename = os.path.basename(filename)
            file_path = os.path.join(BASE_DIR, "evidence", filename)
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
        self.send_error(404, "Evidence image not found")

    def _handle_images_info(self, parsed_path):
        """Sirve una imagen de la carpeta images_info por nombre."""
        query = urllib.parse.parse_qs(parsed_path.query)
        filename = query.get("name", [None])[0]
        if filename:
            filename = os.path.basename(filename)
            from src.config import get_asset_path
            file_path = get_asset_path(os.path.join("images_info", filename))
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
        self.send_error(404, "Manual image not found")

    def _handle_manual(self):
        """Sirve el manual de configuración paso a paso en formato HTML."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        html_manual = """<!DOCTYPE html>
<html>
<head>
    <title>SiGCA Lunch Bot - Manual de Configuración</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { background-color: #010a13; color: #f0e6d2; font-family: 'Outfit', sans-serif; margin: 0; padding: 0; line-height: 1.6; }
        .wrapper { display: flex; min-height: 100vh; }
        .sidebar { width: 280px; background-color: #050c14; border-right: 1px solid #1e2328; padding: 25px; box-sizing: border-box; position: sticky; top: 0; height: 100vh; overflow-y: auto; }
        .sidebar h2 { color: #c8aa6e; font-size: 1.25rem; font-weight: 800; margin-top: 0; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }
        .sidebar ul { list-style: none; padding: 0; margin: 0; }
        .sidebar li { margin-bottom: 12px; }
        .sidebar a { color: #a09b8c; text-decoration: none; font-size: 0.95rem; font-weight: 400; transition: color 0.2s, padding-left: 0.2s; display: block; }
        .sidebar a:hover { color: #0acbe6; padding-left: 5px; }
        .content { flex: 1; padding: 40px; max-width: 900px; box-sizing: border-box; }
        .header { border-bottom: 2px solid #1e2328; padding-bottom: 20px; margin-bottom: 40px; }
        .header h1 { color: #c8aa6e; font-weight: 800; font-size: 2.2rem; margin: 0 0 10px 0; }
        .header p { color: #a09b8c; font-size: 1.1rem; margin: 0; }
        .section { background-color: #091428; border-radius: 12px; border: 1px solid #1e2328; padding: 25px; margin-bottom: 30px; }
        .section h2 { color: #c8aa6e; margin-top: 0; font-size: 1.4rem; border-bottom: 1px solid #1e2328; padding-bottom: 10px; margin-bottom: 15px; }
        .section p { color: #f0e6d2; font-size: 0.95rem; margin-bottom: 20px; }
        .section ul { padding-left: 20px; margin-bottom: 20px; color: #a09b8c; }
        .section li { margin-bottom: 8px; }
        .section strong { color: #f0e6d2; }
        .img-container { background-color: #050c14; border: 1px solid #1e2328; border-radius: 8px; padding: 15px; display: inline-block; max-width: 100%; box-sizing: border-box; }
        .img-container img { max-width: 100%; height: auto; border-radius: 4px; border: 1px solid #1e2328; }
        .sidebar a.btn-back { display: inline-block; background-color: #005a82; color: #ffffff; text-decoration: none; font-weight: 600; padding: 10px 20px; border-radius: 8px; border: 1px solid #0acbe6; transition: background-color 0.2s; margin-top: 20px; text-align: center; }
        .sidebar a.btn-back:hover { background-color: #0acbe6; color: #010a13; padding-left: 20px; }
        .table-container { overflow-x: auto; margin-top: 20px; }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th, td { padding: 12px 15px; border-bottom: 1px solid #1e2328; font-size: 0.9rem; }
        th { background-color: #050c14; color: #c8aa6e; font-weight: 600; }
        td { color: #a09b8c; }
        code { font-family: 'JetBrains Mono', monospace; background-color: #050c14; color: #0acbe6; padding: 2px 6px; border-radius: 4px; font-size: 0.85rem; }
        
        /* Estilos de Notificaciones y popups en el manual */
        .notification-info { border-left: 4px solid #0acbe6; background-color: #050c14; padding: 15px; border-radius: 4px; margin-top: 15px; }
        .notification-success { border-left: 4px solid #0acbe6; background-color: #050c14; padding: 15px; border-radius: 4px; margin-top: 15px; }
        .notification-warning { border-left: 4px solid #785a28; background-color: #050c14; padding: 15px; border-radius: 4px; margin-top: 15px; }
        .notification-error { border-left: 4px solid #c83232; background-color: #050c14; padding: 15px; border-radius: 4px; margin-top: 15px; }
        
        @media (max-width: 768px) {
            .wrapper { flex-direction: column; }
            .sidebar { width: 100%; height: auto; position: static; border-right: none; border-bottom: 1px solid #313244; }
            .content { padding: 20px; }
        }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="sidebar">
            <h2>Índice</h2>
            <ul>
                <li><a href="#intro">Introducción</a></li>
                <li><a href="#sidebar-sec">1. Panel de Control</a></li>
                <li><a href="#sso-sec">2. Autenticación SiGCA</a></li>
                <li><a href="#tg-sec">3. Telegram</a></li>
                <li><a href="#pref-sec">4. Preferencias del Sistema</a></li>
                <li><a href="#scheduler-sec">5. Programador de Tareas</a></li>
                <li><a href="#logs-sec">6. Consola de Logs</a></li>
                <li><a href="#health-sec">7. Salud & API</a></li>
                <li><a href="#buttons-sec">8. Botones de Acción</a></li>
                <li><a href="#env-variables">Variables de Entorno (.env)</a></li>
                <li><a href="#notification-designs">Estilo de Popups y Notificaciones</a></li>
            </ul>
            <a href="/" class="btn-back">Volver al Dashboard</a>
        </div>
        <div class="content">
            <div class="header">
                <h1>Manual de Configuración Completo</h1>
                <p>Guía de uso detallada paso a paso para el bot de almuerzo SiGCABot</p>
            </div>

            <div id="intro" class="section">
                <h2>Introducción</h2>
                <p><strong>SiGCABot</strong> es una herramienta de automatización diseñada para simplificar y asegurar la solicitud diaria de almuerzo en el portal corporativo SiGCA. Está construida con un motor robusto de <strong>Playwright</strong> para simular las interacciones del navegador y una interfaz premium de escritorio en <strong>Tkinter</strong> estructurada bajo la paleta de colores <strong>Catppuccin</strong>.</p>
                <p>A continuación se describe cada una de las secciones y campos de configuración para su puesta en marcha y mantenimiento.</p>
            </div>

            <div id="sidebar-sec" class="section">
                <h2>1. Panel de Control (Sidebar)</h2>
                <p>El panel lateral izquierdo sirve como centro de monitorización del bot:</p>
                <ul>
                    <li><strong>Estado del Servicio:</strong> Muestra un indicador en verde <code>ACTIVO</code> si el bot comprobará automáticamente el almuerzo a la hora establecida, o en rojo <code>INACTIVO</code> si el programador interno está pausado.</li>
                    <li><strong>Último pedido / Resultado:</strong> Refleja la marca de tiempo y el estatus final de la última automatización.</li>
                    <li><strong>Cancelaciones hoy:</strong> Muestra un contador diario. La aplicación restringe la cancelación de pedidos a un máximo de 3 por día para evitar alertas de seguridad y bloqueos corporativos.</li>
                    <li><strong>Check de Cancelación (Hoy):</strong> Controla si se ha cancelado el pedido del día. Este valor se resetea de forma automática al cambiar de fecha.</li>
                </ul>
                <div class="img-container">
                    <img src="/images_info?name=side_bar_panel_control.png" alt="Panel de Control Sidebar">
                </div>
            </div>

            <div id="sso-sec" class="section">
                <h2>2. Ajustes de Autenticación de SiGCA</h2>
                <p>Permite registrar los accesos de inicio de sesión de Microsoft Single Sign-On (SSO):</p>
                <ul>
                    <li><strong>URL del Servicio:</strong> La dirección base del portal corporativo (por defecto <code>https://sigca.ex-cle.com/</code>).</li>
                    <li><strong>Correo Corporativo:</strong> Tu cuenta de Microsoft de la empresa.</li>
                    <li><strong>Contraseña(s):</strong> Contraseñas de acceso. SiGCABot soporta la rotación automática de claves: puedes ingresar múltiples contraseñas separadas por comas (<code>clave1,clave2,clave3</code>) y el bot probará cada una en orden si la anterior expira.</li>
                </ul>
                <div class="img-container">
                    <img src="/images_info?name=autenticacion_sigca.png" alt="Ajustes de Autenticación de SiGCA">
                </div>
            </div>

            <div id="tg-sec" class="section">
                <h2>3. Configuración de Telegram (Alertas y Consultas)</h2>
                <p>El bot incluye interacción remota mediante un bot de Telegram asíncrono:</p>
                <ul>
                    <li><strong>Telegram Bot Token:</strong> Token de seguridad obtenido desde @BotFather al crear el bot de Telegram.</li>
                    <li><strong>Telegram Chat ID:</strong> ID numérico de tu chat personal (obtenido con bots como @userinfobot) o el ID de un canal/grupo donde se reportarán los estados y evidencias.</li>
                    <li><strong>Probar Telegram:</strong> Envía un mensaje instantáneo de verificación para confirmar que las credenciales del API de Telegram son correctas.</li>
                </ul>
                <div class="img-container">
                    <img src="/images_info?name=telegram_config.png" alt="Configuración de Telegram">
                </div>
            </div>

            <div id="pref-sec" class="section">
                <h2>4. Ajustes y Preferencias del Sistema</h2>
                <p>Preferencias de ejecución del bot:</p>
                <ul>
                    <li><strong>Menú Favorito:</strong> Puedes priorizar la solicitud del menú <code>Saludable</code> o <code>Estándar</code>. Si el favorito no se encuentra disponible en la intranet corporativa ese día, el bot seleccionará automáticamente la opción alternativa para asegurar la comida.</li>
                    <li><strong>Revisión (Hora:Minuto):</strong> La hora del día en formato 24 horas a la que el planificador local del bot despertará para intentar solicitar el almuerzo de forma automática.</li>
                    <li><strong>Iniciar automáticamente con Windows:</strong> Agrega una entrada en el Registro de Windows del usuario para iniciar la GUI minimizada en la bandeja del sistema al arrancar el ordenador.</li>
                </ul>
                <div class="img-container">
                    <img src="/images_info?name=ajustes_preferencias_sistemas.png" alt="Ajustes y Preferencias del Sistema">
                </div>
            </div>

            <div id="scheduler-sec" class="section">
                <h2>5. Programador de Tareas de Windows</h2>
                <p>Permite registrar la automatización como una Tarea del Sistema de Windows para máxima confiabilidad:</p>
                <ul>
                    <li><strong>Registrar Tarea Diaria:</strong> Lanza un comando de PowerShell (solicitando elevación de permisos mediante UAC de Windows) que registra la ejecución del bot a nivel de sistema. Esto garantiza que el bot realice el intento de pedido incluso si el usuario ha cerrado la ventana de la aplicación.</li>
                    <li><strong>Eliminar Tarea:</strong> Desvincula de forma permanente el bot del Programador de Tareas de Windows de forma segura.</li>
                </ul>
                <div class="img-container">
                    <img src="/images_info?name=programar_tareas_windows.png" alt="Programador de Tareas de Windows">
                </div>
            </div>

            <div id="logs-sec" class="section">
                <h2>6. Consola de Logs en Tiempo Real</h2>
                <p>Muestra el log de eventos estructurado y con código de colores según su severidad:</p>
                <ul>
                    <li><strong style="color:#89b4fa;">Celeste (INFO):</strong> Indica un flujo normal (ej. 'Iniciando navegación', 'Guardando configuración').</li>
                    <li><strong style="color:#f9e2af;">Amarillo (WARNING):</strong> Advertencias que no detienen el flujo (ej. 'Reintentando conexión con Telegram').</li>
                    <li><strong style="color:#f38ba8;">Rojo (ERROR/CRITICAL):</strong> Errores críticos que impiden el pedido (ej. 'Contraseñas expiradas', 'Selector del botón no encontrado').</li>
                </ul>
                <div class="img-container">
                    <img src="/images_info?name=console_log_section.png" alt="Consola de Logs">
                </div>
            </div>

            <div id="health-sec" class="section">
                <h2>7. Monitoreo de Salud & API</h2>
                <p>El bot incorpora un micro-servidor web para interactuar y revisar el estado externamente:</p>
                <ul>
                    <li><strong>URL del Health Check:</strong> Endpoint en formato JSON (<code>http://127.0.0.1:18293/health</code>) ideal para integrar con herramientas de monitoreo externas.</li>
                    <li><strong>Dashboard Visual:</strong> Interfaz web interactiva en <code>http://127.0.0.1:18293/</code> que muestra el estado de salud, los logs recientes y la última captura de pantalla tomada en el portal corporativo.</li>
                    <li><strong>Botones de Mantenimiento:</strong> Accesos directos para explorar la carpeta <code>/evidence</code> (donde se almacenan los comprobantes PNG de pedidos) y para limpiar registros y caches históricos innecesarios.</li>
                </ul>
                <div class="img-container">
                    <img src="/images_info?name=seccion_salud_api.png" alt="Monitoreo de Salud & API">
                </div>
            </div>

            <div id="buttons-sec" class="section">
                <h2>8. Botones de Acción del Sistema</h2>
                <p>Acciones fundamentales para interactuar inmediatamente con el motor:</p>
                <ul>
                    <li><strong>Guardar Configuración:</strong> Valida y escribe los cambios en los ficheros locales persistentes (<code>.env</code> y <code>config.json</code>).</li>
                    <li><strong>Simular Pedido (Dry Run):</strong> Lanza un navegador invisible (Playwright) para realizar todo el flujo de inicio de sesión y llenado de datos, pero se detiene justo antes de dar clic al botón de confirmar pedido. Excelente para validar si tus contraseñas y correos funcionan.</li>
                    <li><strong>Solicitud Manual:</strong> Fuerza una ejecución automática real del bot de forma inmediata, saltándose el horario diario establecido y omitiendo los bloqueos por cancelación.</li>
                </ul>
                <div class="img-container">
                    <img src="/images_info?name=botones_del_sistema.png" alt="Botones de Acción del Sistema">
                </div>
            </div>

            <div id="env-variables" class="section">
                <h2>Variables de Entorno (.env)</h2>
                <p>El bot persiste los parámetros críticos de seguridad en el archivo <code>.env</code> en la raíz del ejecutable. A continuación se resume su funcionalidad:</p>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Variable</th>
                                <th>Propósito</th>
                                <th>Ejemplo / Formato</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><code>SIGCA_URL</code></td>
                                <td>Dirección web de la intranet corporativa de SiGCA.</td>
                                <td><code>https://sigca.ex-cle.com/</code></td>
                            </tr>
                            <tr>
                                <td><code>SIGCA_USER</code></td>
                                <td>Correo institucional Microsoft SSO.</td>
                                <td><code>usuario@ex-cle.com</code></td>
                            </tr>
                            <tr>
                                <td><code>SIGCA_PASSWORDS</code></td>
                                <td>Lista de contraseñas separadas por comas (para rotación).</td>
                                <td><code>ClaveJulio2026,ClaveAgosto2026</code></td>
                            </tr>
                            <tr>
                                <td><code>TELEGRAM_TOKEN</code></td>
                                <td>Token del bot de Telegram para notificaciones externas.</td>
                                <td><code>123456789:ABCdefGhIJKlmNoPQRsT...</code></td>
                            </tr>
                            <tr>
                                <td><code>TELEGRAM_CHAT_ID</code></td>
                                <td>ID numérico del chat destinatario para las notificaciones.</td>
                                <td><code>987654321</code></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div id="notification-designs" class="section">
                <h2>Estilo de Popups y Notificaciones del Bot</h2>
                <p>Con el fin de ofrecer una experiencia Premium y unificada con la paleta <strong>Catppuccin</strong> de modo oscuro, la aplicación tiene prohibido el uso de ventanas nativas del sistema operativo. Los popups del sistema siguen las siguientes directrices:</p>
                
                <div class="notification-info">
                    <strong>ℹ Información (Info):</strong> Utiliza el color de realce celeste <code>#89b4fa</code> para su borde e icono circular de estado. Se usa para notificar acciones completadas o cargas neutras.
                </div>
                <div class="notification-success">
                    <strong>✓ Éxito (Success):</strong> Enmarcada con el tono verde <code>#a6e3a1</code>. Aparece únicamente cuando se confirma un pedido manual, simulación exitosa o guardado correcto de configuración.
                </div>
                <div class="notification-warning">
                    <strong>⚠ Advertencia (Warning):</strong> Borde exterior amarillo <code>#f9e2af</code>. Se dispara ante alertas críticas que permiten continuar la ejecución, como la confirmación de la cancelación diaria.
                </div>
                <div class="notification-error">
                    <strong>❌ Error / Crítico (Error):</strong> Destaca con el color rojo <code>#f38ba8</code>. Se muestra cuando la automatización falla, las claves están vacías o la red impide conectar con los servidores corporativos.
                </div>
                <p style="margin-top: 20px;">Cada botón de acción ("Aceptar", "Sí", "No") dentro de estos modales de Tkinter implementa hover dinámico que se oscurece automáticamente al posicionar el cursor sobre él, manteniendo la interactividad fluida.</p>
            </div>
        </div>
    </div>
</body>
</html>"""
        self.wfile.write(html_manual.encode("utf-8"))

    def _handle_dashboard(self):

        """Dashboard HTML visual con estado del bot."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        status_data = load_status()
        active_badge = (
            '<span class="badge badge-success">SISTEMA ACTIVO</span>'
            if status_data.get("is_active", True)
            else '<span class="badge badge-danger">SISTEMA INACTIVO</span>'
        )

        # Buscar última imagen en evidence/
        evidence_dir = os.path.join(BASE_DIR, "evidence")
        img_html = "<div style='color: #a09b8c; padding: 40px; text-align: center; border: 2px dashed #1e2328; border-radius: 8px; background-color: #050c14;'>Sin capturas disponibles</div>"
        last_img = "N/A"
        if os.path.exists(evidence_dir):
            files = [f for f in os.listdir(evidence_dir) if f.endswith(".png")]
            if files:
                files.sort(key=lambda x: os.path.getmtime(os.path.join(evidence_dir, x)), reverse=True)
                last_img = files[0]
                img_html = f"<img src='/evidence?name={last_img}' alt='Última Evidencia' class='img-fluid shadow'>"

        # Leer logs recientes
        log_path = os.path.join(BASE_DIR, "logs", "lunch_automation.log")
        log_content = "Sin logs registrados"
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    log_lines = f.readlines()[-20:]
                    log_content = "".join(log_lines)
            except Exception:
                pass

        last_run_ts = status_data.get("last_run_timestamp", "Nunca")
        last_run_status = status_data.get("last_run_status", "N/A")
        status_color = '#0acbe6' if last_run_status == 'success' else '#c83232'

        html_page = f"""<!DOCTYPE html>
<html>
<head>
    <title>SiGCA Lunch Bot - Health Check</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        body {{ background-color: #010a13; color: #f0e6d2; font-family: 'Outfit', sans-serif; margin: 0; padding: 20px; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        h1 {{ color: #c8aa6e; font-weight: 800; margin-bottom: 5px; }}
        .card {{ background-color: #091428; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #1e2328; }}
        .grid {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; }}
        @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
        .badge {{ padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 0.95rem; }}
        .badge-success {{ background-color: #0acbe6; color: #010a13; }}
        .badge-danger {{ background-color: #c83232; color: #ffffff; }}
        .img-fluid {{ max-width: 100%; height: auto; border-radius: 8px; border: 1px solid #1e2328; }}
        pre {{ background-color: #050c14; padding: 15px; border-radius: 8px; overflow-x: auto; color: #0acbe6; font-family: Consolas, monospace; font-size: 0.85rem; max-height: 350px; white-space: pre-wrap; }}
        .title-wrapper {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #1e2328; padding-bottom: 15px; margin-bottom: 20px; }}
        strong {{ color: #f0e6d2; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="title-wrapper">
            <div>
                <h1>SiGCA Lunch Bot Dashboard</h1>
                <small style="color: #a09b8c;">Health Check Web en vivo — Hextech Client</small>
            </div>
            <div>{active_badge}</div>
        </div>
        <div class="grid">
            <div>
                <div class="card">
                    <h2 style="color: #c8aa6e; margin-top:0; border-bottom: 1px solid #1e2328; padding-bottom: 8px;">Estado General</h2>
                    <p><strong>Estatus:</strong> Saludable (Funcionando)</p>
                    <p><strong>Última Ejecución:</strong> {last_run_ts}</p>
                    <p><strong>Último Resultado:</strong> <span style="color: {status_color}">{last_run_status.upper()}</span></p>
                </div>
                <div class="card">
                    <h2 style="color: #0acbe6; margin-top:0; border-bottom: 1px solid #1e2328; padding-bottom: 8px;">Logs Recientes</h2>
                    <pre>{log_content}</pre>
                </div>
            </div>
            <div>
                <div class="card">
                    <h2 style="color: #c8aa6e; margin-top:0; border-bottom: 1px solid #1e2328; padding-bottom: 8px;">Última Captura de Evidencia</h2>
                    <p style="color: #a09b8c; font-size: 0.9rem;">Archivo: {last_img}</p>
                    {img_html}
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
        self.wfile.write(html_page.encode("utf-8"))


def start_http_server():
    """Inicia el servidor HTTP de health check en un hilo secundario."""
    port = 18293
    handler = HealthCheckHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        logger.info(f"Servidor HTTP Health Check iniciado en http://127.0.0.1:{port}/")
        while not state.stop_threads:
            httpd.handle_request()
