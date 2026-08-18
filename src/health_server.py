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

from src.config import BASE_DIR, load_status, APP_VERSION
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
        active = status_data.get("is_active", True)
        last_status = status_data.get("last_run_status", "N/A")
        service_status = "paused" if not active else (
            "error" if str(last_status).lower().startswith("error") else "ok"
        )
        response = {
            "status": service_status,
            "active": active,
            "last_run": status_data.get("last_run_timestamp", "Nunca"),
            "last_status": last_status,
            "version": APP_VERSION
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
            .sidebar { width: 100%; height: auto; position: static; border-right: none; border-bottom: 1px solid #1e2328; }
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
                <p><strong>SiGCABot</strong> es una herramienta de automatización diseñada para simplificar y asegurar la solicitud diaria de almuerzo en el portal corporativo SiGCA. Está construida con un motor robusto de <strong>Playwright</strong> para simular las interacciones del navegador y una interfaz premium de escritorio en <strong>Tkinter</strong> estructurada bajo la paleta de colores <strong>Hextech Client</strong>.</p>
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
                    <li><strong style="color:#005a82;">Azul (INFO):</strong> Indica un flujo normal (ej. 'Iniciando navegación', 'Guardando configuración').</li>
                    <li><strong style="color:#785a28;">Bronce (WARNING):</strong> Advertencias que no detienen el flujo (ej. 'Reintentando conexión con Telegram').</li>
                    <li><strong style="color:#c83232;">Rojo (ERROR/CRITICAL):</strong> Errores críticos que impiden el pedido (ej. 'Credenciales inválidas', 'Selector del botón no encontrado').</li>
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
                <p>Con el fin de ofrecer una experiencia Premium y unificada con la paleta <strong>Hextech Client</strong> de modo oscuro, la aplicación tiene prohibido el uso de ventanas nativas del sistema operativo. Los popups del sistema siguen las siguientes directrices:</p>
                
                <div class="notification-info">
                    <strong>ℹ Información (Info):</strong> Utiliza el color azul <code>#005a82</code> para su borde e icono circular de estado. Se usa para notificar acciones completadas o cargas neutras.
                </div>
                <div class="notification-success">
                    <strong>✓ Éxito (Success):</strong> Enmarcada con el tono cian <code>#0acbe6</code>. Aparece únicamente cuando se confirma un pedido manual, simulación exitosa o guardado correcto de configuración.
                </div>
                <div class="notification-warning">
                    <strong>⚠ Advertencia (Warning):</strong> Borde exterior bronce <code>#785a28</code>. Se dispara ante alertas críticas que permiten continuar la ejecución, como la confirmación de la cancelación diaria.
                </div>
                <div class="notification-error">
                    <strong>❌ Error / Crítico (Error):</strong> Destaca con el color rojo <code>#c83232</code>. Se muestra cuando la automatización falla, las claves están vacías o la red impide conectar con los servidores corporativos.
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
        img_html = "<div style='color: #a09b8c; padding: 60px 20px; text-align: center; border: 2px dashed #1e2328; border-radius: 8px; background-color: #050c14;'><span style='font-size: 2rem; display: block; margin-bottom: 10px;'>📷</span>Sin capturas de evidencia disponibles</div>"
        last_img = "N/A"
        has_image = False
        if os.path.exists(evidence_dir):
            files = [f for f in os.listdir(evidence_dir) if f.endswith(".png")]
            if files:
                files.sort(key=lambda x: os.path.getmtime(os.path.join(evidence_dir, x)), reverse=True)
                last_img = files[0]
                has_image = True
                img_html = f"""
                <div class="evidence-container">
                    <div class="evidence-toolbar">
                        <span class="evidence-filename">📄 {last_img}</span>
                        <div class="evidence-actions">
                            <a href="/evidence?name={last_img}" target="_blank" class="btn-tool" title="Abrir imagen original en pestaña nueva">↗ Abrir Original</a>
                            <button type="button" class="btn-tool btn-zoom" onclick="openLightbox('/evidence?name={last_img}')" title="Ver en pantalla completa con zoom">🔍 Pantalla Completa</button>
                        </div>
                    </div>
                    <div class="evidence-preview-wrapper" onclick="openLightbox('/evidence?name={last_img}')" title="Haz clic para ampliar">
                        <img src='/evidence?name={last_img}' alt='Última Evidencia' class='img-fluid shadow evidence-img'>
                        <div class="evidence-overlay"><span>🔍 Clic para ampliar en alta resolución</span></div>
                    </div>
                </div>
                """

        # Leer logs recientes
        log_path = os.path.join(BASE_DIR, "logs", "lunch_automation.log")
        log_content = "Sin logs registrados"
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    log_lines = f.readlines()[-25:]
                    log_content = "".join(log_lines)
            except Exception:
                pass

        last_run_ts = status_data.get("last_run_timestamp", "Nunca")
        last_run_status = status_data.get("last_run_status", "N/A")
        service_status_text = "Activo" if status_data.get("is_active", True) else "Pausado manualmente"
        if last_run_status == 'success':
            status_color = '#0acbe6'
            status_icon = '✅'
        elif last_run_status in ('skipped', 'dry_run_success'):
            status_color = '#c8aa6e'
            status_icon = '⚡'
        else:
            status_color = '#c83232'
            status_icon = '❌'

        html_page = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <title>SiGCA Lunch Bot - Health Check & Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            background-color: #010a13;
            color: #f0e6d2;
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 24px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1480px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 15px;
            border-bottom: 2px solid #1e2328;
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        .header h1 {{
            color: #c8aa6e;
            font-weight: 800;
            font-size: 1.9rem;
            margin: 0 0 4px 0;
            letter-spacing: -0.5px;
        }}
        .header p {{
            color: #a09b8c;
            margin: 0;
            font-size: 0.95rem;
        }}
        .header-actions {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .badge {{
            padding: 8px 18px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .badge-success {{
            background-color: #0acbe6;
            color: #010a13;
            box-shadow: 0 0 15px rgba(10, 203, 230, 0.25);
        }}
        .badge-danger {{
            background-color: #c83232;
            color: #ffffff;
            box-shadow: 0 0 15px rgba(200, 50, 50, 0.25);
        }}
        .btn-header {{
            background-color: #091428;
            border: 1px solid #1e2328;
            color: #c8aa6e;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn-header:hover {{
            background-color: #005a82;
            color: #f0e6d2;
            border-color: #0acbe6;
        }}

        /* Grid principal */
        .dashboard-grid {{
            display: grid;
            grid-template-columns: minmax(360px, 480px) 1fr;
            gap: 24px;
            align-items: start;
        }}
        @media (max-width: 1024px) {{
            .dashboard-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .card {{
            background-color: #091428;
            border-radius: 14px;
            padding: 22px;
            margin-bottom: 24px;
            border: 1px solid #1e2328;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            transition: border-color 0.2s ease;
        }}
        .card:hover {{
            border-color: #2b3a4a;
        }}
        .card h2 {{
            color: #c8aa6e;
            font-size: 1.2rem;
            font-weight: 700;
            margin-top: 0;
            margin-bottom: 16px;
            border-bottom: 1px solid #1e2328;
            padding-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .status-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .status-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #0d1b2a;
            font-size: 0.95rem;
        }}
        .status-item:last-child {{
            border-bottom: none;
        }}
        .status-label {{
            color: #a09b8c;
            font-weight: 500;
        }}
        .status-value {{
            color: #f0e6d2;
            font-weight: 600;
        }}

        /* Consola de logs */
        pre.logs-box {{
            background-color: #050c14;
            padding: 16px;
            border-radius: 10px;
            border: 1px solid #1e2328;
            overflow-x: auto;
            color: #0acbe6;
            font-family: 'JetBrains Mono', Consolas, monospace;
            font-size: 0.8rem;
            line-height: 1.45;
            max-height: 480px;
            white-space: pre-wrap;
            margin: 0;
        }}

        /* Contenedor de Evidencia Ampliada */
        .evidence-card {{
            display: flex;
            flex-direction: column;
        }}
        .evidence-container {{
            background-color: #050c14;
            border: 1px solid #1e2328;
            border-radius: 10px;
            overflow: hidden;
        }}
        .evidence-toolbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
            padding: 12px 16px;
            background-color: #07101c;
            border-bottom: 1px solid #1e2328;
        }}
        .evidence-filename {{
            color: #a09b8c;
            font-size: 0.85rem;
            font-family: 'JetBrains Mono', monospace;
            word-break: break-all;
        }}
        .evidence-actions {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .btn-tool {{
            background-color: #091428;
            border: 1px solid #1e2328;
            color: #f0e6d2;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s ease;
            font-family: inherit;
        }}
        .btn-tool:hover {{
            background-color: #005a82;
            border-color: #0acbe6;
            color: #ffffff;
        }}
        .evidence-preview-wrapper {{
            position: relative;
            cursor: zoom-in;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #02070d;
            padding: 10px;
            min-height: 520px;
        }}
        .evidence-img {{
            width: 100%;
            height: auto;
            max-height: 780px;
            object-fit: contain;
            border-radius: 6px;
            transition: transform 0.2s ease;
        }}
        .evidence-overlay {{
            position: absolute;
            bottom: 20px;
            background-color: rgba(9, 20, 40, 0.88);
            color: #0acbe6;
            border: 1px solid #0acbe6;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            pointer-events: none;
            backdrop-filter: blur(4px);
            opacity: 0.9;
            transition: opacity 0.2s;
        }}
        .evidence-preview-wrapper:hover .evidence-overlay {{
            opacity: 1;
            background-color: rgba(0, 90, 130, 0.95);
            color: #ffffff;
        }}

        /* Lightbox Modal de Pantalla Completa */
        .lightbox-modal {{
            display: none;
            position: fixed;
            z-index: 9999;
            left: 0;
            top: 0;
            width: 100vw;
            height: 100vh;
            background-color: rgba(1, 10, 19, 0.94);
            backdrop-filter: blur(8px);
            overflow: auto;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .lightbox-modal.active {{
            display: flex;
        }}
        .lightbox-content-wrapper {{
            position: relative;
            max-width: 95vw;
            max-height: 95vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .lightbox-img {{
            max-width: 95vw;
            max-height: 88vh;
            object-fit: contain;
            border-radius: 8px;
            border: 2px solid #0acbe6;
            box-shadow: 0 0 40px rgba(10, 203, 230, 0.3);
        }}
        .lightbox-header {{
            position: absolute;
            top: -45px;
            right: 0;
            display: flex;
            gap: 12px;
        }}
        .btn-close-lightbox {{
            background: #c83232;
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 0.9rem;
            font-weight: 700;
            cursor: pointer;
            transition: opacity 0.2s;
        }}
        .btn-close-lightbox:hover {{
            opacity: 0.85;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div>
                <h1>SiGCA Lunch Bot Dashboard</h1>
                <p>Health Check Web en vivo — Hextech Client v{APP_VERSION}</p>
            </div>
            <div class="header-actions">
                {active_badge}
                <a href="/manual" class="btn-header">📖 Manual</a>
                <button type="button" class="btn-header" onclick="location.reload()">🔄 Refrescar</button>
            </div>
        </header>

        <main class="dashboard-grid">
            <!-- Columna Izquierda: Estado y Logs -->
            <section>
                <div class="card">
                    <h2>📊 Estado General</h2>
                    <ul class="status-list">
                        <li class="status-item">
                            <span class="status-label">Estatus del Servicio:</span>
                            <span class="status-value">{service_status_text}</span>
                        </li>
                        <li class="status-item">
                            <span class="status-label">Última Ejecución:</span>
                            <span class="status-value">{last_run_ts}</span>
                        </li>
                        <li class="status-item">
                            <span class="status-label">Último Resultado:</span>
                            <span class="status-value" style="color: {status_color};">{status_icon} {last_run_status.upper()}</span>
                        </li>
                        <li class="status-item">
                            <span class="status-label">Versión de SiGCABot:</span>
                            <span class="status-value">v{APP_VERSION}</span>
                        </li>
                    </ul>
                </div>

                <div class="card">
                    <h2>💻 Logs Recientes</h2>
                    <pre class="logs-box">{log_content}</pre>
                </div>
            </section>

            <!-- Columna Derecha: Gran Visor de Evidencia -->
            <section>
                <div class="card evidence-card">
                    <h2>📸 Última Captura de Evidencia</h2>
                    {img_html}
                </div>
            </section>
        </main>
    </div>

    <!-- Lightbox Modal para Visualización en Alta Resolución -->
    <div id="lightboxModal" class="lightbox-modal" onclick="closeLightbox(event)">
        <div class="lightbox-content-wrapper" onclick="event.stopPropagation()">
            <div class="lightbox-header">
                <a id="lightboxDownloadBtn" href="#" target="_blank" class="btn-tool" style="background:#091428; border-color:#0acbe6; color:#0acbe6;">↗ Abrir Pestaña</a>
                <button type="button" class="btn-close-lightbox" onclick="closeLightbox()">✕ Cerrar (Esc)</button>
            </div>
            <img id="lightboxImg" src="" alt="Evidencia Ampliada" class="lightbox-img">
        </div>
    </div>

    <script>
        function openLightbox(src) {{
            const modal = document.getElementById('lightboxModal');
            const img = document.getElementById('lightboxImg');
            const downloadBtn = document.getElementById('lightboxDownloadBtn');
            img.src = src;
            downloadBtn.href = src;
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        function closeLightbox(e) {{
            const modal = document.getElementById('lightboxModal');
            modal.classList.remove('active');
            document.body.style.overflow = 'auto';
        }}

        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                closeLightbox();
            }}
        }});
    </script>
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
