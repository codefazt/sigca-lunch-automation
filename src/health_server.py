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
            "version": "2.1.0"
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

    def _handle_dashboard(self):
        """Dashboard HTML visual con estado del bot."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        status_data = load_status()
        active_badge = (
            '<span class="badge badge-success">ACTIVO</span>'
            if status_data.get("is_active", True)
            else '<span class="badge badge-danger">INACTIVO</span>'
        )

        # Buscar última imagen en evidence/
        evidence_dir = os.path.join(BASE_DIR, "evidence")
        img_html = "<div style='color: #6c7086; padding: 40px; text-align: center; border: 2px dashed #313244; border-radius: 8px;'>Sin capturas disponibles</div>"
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
        status_color = '#a6e3a1' if last_run_status == 'success' else '#f38ba8'

        html_page = f"""<!DOCTYPE html>
<html>
<head>
    <title>SiGCA Lunch Bot - Health Check</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        body {{ background-color: #1e1e2e; color: #cdd6f4; font-family: 'Outfit', sans-serif; margin: 0; padding: 20px; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        h1 {{ color: #b4befe; font-weight: 800; margin-bottom: 5px; }}
        .card {{ background-color: #252538; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #313244; }}
        .grid {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; }}
        @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
        .badge {{ padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 0.95rem; }}
        .badge-success {{ background-color: #a6e3a1; color: #11111b; }}
        .badge-danger {{ background-color: #f38ba8; color: #11111b; }}
        .img-fluid {{ max-width: 100%; height: auto; border-radius: 8px; border: 1px solid #45475a; }}
        pre {{ background-color: #11111b; padding: 15px; border-radius: 8px; overflow-x: auto; color: #a6e3a1; font-family: Consolas, monospace; font-size: 0.85rem; max-height: 350px; white-space: pre-wrap; }}
        .title-wrapper {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #313244; padding-bottom: 15px; margin-bottom: 20px; }}
        strong {{ color: #f5e0dc; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="title-wrapper">
            <div>
                <h1>SiGCA Lunch Bot Dashboard</h1>
                <small style="color: #6c7086;">Health Check Web en vivo</small>
            </div>
            <div>{active_badge}</div>
        </div>
        <div class="grid">
            <div>
                <div class="card">
                    <h2 style="color: #f5c2e7; margin-top:0; border-bottom: 1px solid #313244; padding-bottom: 8px;">Estado General</h2>
                    <p><strong>Estatus:</strong> Saludable (Funcionando)</p>
                    <p><strong>Última Ejecución:</strong> {last_run_ts}</p>
                    <p><strong>Último Resultado:</strong> <span style="color: {status_color}">{last_run_status.upper()}</span></p>
                </div>
                <div class="card">
                    <h2 style="color: #89b4fa; margin-top:0; border-bottom: 1px solid #313244; padding-bottom: 8px;">Logs Recientes</h2>
                    <pre>{log_content}</pre>
                </div>
            </div>
            <div>
                <div class="card">
                    <h2 style="color: #fab387; margin-top:0; border-bottom: 1px solid #313244; padding-bottom: 8px;">Última Captura de Evidencia</h2>
                    <p style="color: #a6adc8; font-size: 0.9rem;">Archivo: {last_img}</p>
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
